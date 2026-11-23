import asyncio
from datetime import datetime
import pandas as pd
import streamlit as st
from telethon import TelegramClient
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChatBannedRights, ChannelParticipantsAdmins

# ================= إعدادات الأمان والمفاتيح =================
try:
    API_ID = int(st.secrets["API_ID"])
    API_HASH = st.secrets["API_HASH"]
    APP_PASSWORD = str(st.secrets.get("APP_PASSWORD", "12345"))
except Exception:
    API_ID = 0
    API_HASH = ""
    APP_PASSWORD = "12345"

st.set_page_config(page_title="تصفية الجروب | Smart Manager", page_icon="💠", layout="wide")

# ================= التصميم العصري (Modern Dark Glassmorphism) =================
modern_glass_css = """
<style>
    @import url('https://googleapis.com');

    .stApp {
        background: radial-gradient(circle at 15% 15%, #162238 0%, #090d16 55%, #05070c 100%);
        color: #f1f5f9;
        font-family: 'Tajawal', sans-serif;
    }

    h1, h2, h3, label, .stMarkdown p {
        font-family: 'Tajawal', sans-serif !important;
        color: #f8fafc !important;
    }

    .hero-banner {
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.15) 0%, rgba(129, 140, 248, 0.15) 100%);
        border: 1px solid rgba(56, 189, 248, 0.3);
        backdrop-filter: blur(12px);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    }
    .hero-banner h1 {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.3rem;
        margin: 0;
    }
    .hero-banner p {
        color: #94a3b8 !important;
        margin-top: 6px;
        font-size: 1rem;
    }

    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.55);
        border: 1px solid rgba(148, 163, 184, 0.15);
        backdrop-filter: blur(10px);
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        border-color: rgba(56, 189, 248, 0.5);
    }
    [data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
    }

    .stTextArea textarea, .stTextInput input, [data-testid="stFileUploader"] {
        background-color: rgba(15, 23, 42, 0.75) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        border-radius: 12px !important;
        padding: 10px !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.25) !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 20px !important;
        font-family: 'Tajawal', sans-serif !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        box-shadow: 0 4px 15px rgba(2, 132, 199, 0.4);
        transition: all 0.25s ease !important;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(79, 70, 229, 0.6);
        filter: brightness(1.1);
    }

    header, #MainMenu, footer {visibility: hidden;}
</style>
"""
st.markdown(modern_glass_css, unsafe_allow_html=True)

# ================= 1. شاشة تسجيل الدخول =================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
        <div class="hero-banner">
            <h1>💠 نظام تصفية الجروب الذكي</h1>
            <p>بوابة الإدارة المحمية — يرجى إدخال رمز المرور للمتابعة</p>
        </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        pwd = st.text_input("كلمة المرور", type="password", placeholder="••••••••")
        if st.button("تسجيل الدخول ➔"):
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("كلمة المرور غير صحيحة، حاول مرة أخرى.")
    st.stop()

# ================= إدارة الحالة =================
defaults = {
    "page": "home",
    "scan_results": [],
    "stats": {},
    "kicked_report": [],
    "scanned_groups": [],
    "dup_info": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("""
    <div class="hero-banner">
        <h1>💠 نظام تصفية وإدارة جروبات تليجرام</h1>
        <p>لوحة تحكم ذكية لمطابقة البيانات، حماية المشرفين، وتصفية الأعضاء بضغطة زر</p>
    </div>
""", unsafe_allow_html=True)

# ================= دوال الاتصال بتليجرام =================
async def scan_groups(groups, allowed_users, allowed_phones):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        st.error("ملف الجلسة (my_session.session) غير صالح أو منتهي!")
        await client.disconnect()
        return [], {}

    results = []
    total_members = 0
    matched_users = set()

    for link in groups:
        link = link.strip()
        if not link:
            continue
        try:
            entity = await client.get_entity(link)
            group_title = getattr(entity, 'title', link)

            admins = await client.get_participants(entity, filter=ChannelParticipantsAdmins)
            admin_ids = {adm.id for adm in admins}

            participants = await client.get_participants(entity)
            for user in participants:
                if user.bot or user.deleted or user.is_self:
                    continue
                total_members += 1

                if user.id in admin_ids:
                    continue

                username = user.username.lower() if user.username else None
                user_phone = user.phone[-10:] if (user.phone and len(user.phone) >= 10) else None

                in_users = username in allowed_users
                in_phones = user_phone in allowed_phones

                if in_users:
                    matched_users.add(username)

                if not (in_users or in_phones):
                    results.append({
                        "تحديد": True,
                        "الجروب": group_title,
                        "group_link": link,
                        "user_id": user.id,
                        "الاسم على تليجرام": user.first_name or "بدون اسم",
                        "اليوزر": f"@{username}" if username else "لا يوجد",
                        "رقم الهاتف": user.phone if user.phone else "مخفي",
                        "حساب وهمي": (username is None and user_phone is None)
                    })
        except Exception as e:
            st.error(f"تعذر فحص الجروب ({link}): {e}")

    await client.disconnect()
    not_joined_count = max(0, len(allowed_users) - len(matched_users))
    stats = {
        "total": total_members,
        "registered": total_members - len(results),
        "to_kick": len(results),
        "not_joined": not_joined_count
    }
    return results, stats

async def execute_action(selected_rows, is_permanent_ban):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    ban_rights = ChatBannedRights(until_date=None, view_messages=True)
    unban_rights = ChatBannedRights(until_date=None)

    progress = st.progress(0)
    status_box = st.empty()
    timer_box = st.empty()
    report = []
    total_targets = len(selected_rows)

    for idx, row in enumerate(selected_rows):
        remaining = (total_targets - idx) * 3
        mins, secs = divmod(remaining, 60)
        timer_box.caption(f"⏱️ الوقت المتبقي التقريبي: {mins} دقيقة و {secs} ثانية")
        try:
            await client(EditBannedRequest(row["group_link"], int(row["user_id"]), ban_rights))
            if not is_permanent_ban:
                await client(EditBannedRequest(row["group_link"], int(row["user_id"]), unban_rights))

            action_type = "حظر نهائي" if is_permanent_ban else "طرد عادي"
            status_box.success(f"تم تنفيذ ({action_type}) على: {row['الاسم على تليجرام']} ({idx+1}/{total_targets})")
            report.append({
                "الاسم": row["الاسم على تليجرام"],
                "اليوزر": row["اليوزر"],
                "رقم الهاتف": row["رقم الهاتف"],
                "الجروب": row["الجروب"],
                "الإجراء": action_type,
                "الوقت": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            await asyncio.sleep(3)
        except Exception as e:
            st.warning(f"تعذر تنفيذ الإجراء مع {row['الاسم على تليجرام']}: {e}")
        progress.progress((idx + 1) / total_targets)

    timer_box.empty()
    await client.disconnect()
    return report

async def send_warning_msg(groups, msg_text):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    for link in groups:
        clean_link = link.strip()
        if clean_link:
            try:
                await client.send_message(clean_link, msg_text)
            except Exception as e:
                st.error(f"فشل إرسال الرسالة لـ {clean_link}: {e}")
    await client.disconnect()

async def revoke_invite_links(groups):

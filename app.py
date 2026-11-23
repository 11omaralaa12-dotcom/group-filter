import asyncio
from datetime import datetime
import pandas as pd
import streamlit as st
from telethon import TelegramClient
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChatBannedRights

# ================= إعدادات الأمان والمفاتيح =================
try:
    API_ID = int(st.secrets["API_ID"])
    API_HASH = st.secrets["API_HASH"]
    APP_PASSWORD = str(st.secrets.get("APP_PASSWORD", "12345"))
except Exception:
    API_ID = 0
    API_HASH = ""
    APP_PASSWORD = "12345"

st.set_page_config(page_title="تصفية الجروب | Ultimate Control Panel", page_icon="👨‍💻", layout="wide")

# ================= تصميم الهاكر النظيف (بدون أي تغطية للعناصر) =================
hacker_style = """
<style>
    @import url('https://googleapis.com');
    .stApp {
        background-color: #020502;
        background-image: radial-gradient(#003b0f 1px, transparent 1px);
        background-size: 24px 24px;
        color: #00FF41;
        font-family: 'Cairo', 'Fira Code', monospace;
    }
    h1, h2, h3, label, .stMarkdown p, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        color: #00FF41 !important; text-shadow: 0 0 8px rgba(0, 255, 65, 0.5); font-family: 'Cairo', monospace !important;
    }
    .stTextArea textarea, .stTextInput input, [data-testid="stFileUploader"] {
        background-color: #071207 !important; color: #00FF41 !important; border: 1px solid #00FF41 !important;
    }
    .stButton > button {
        background-color: #002609 !important; color: #00FF41 !important; border: 2px solid #00FF41 !important;
        font-weight: bold !important; font-size: 18px !important; padding: 10px !important;
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.4); width: 100%; transition: 0.3s;
    }
    .stButton > button:hover { background-color: #00FF41 !important; color: #000 !important; box-shadow: 0 0 25px #00FF41; }
    header {visibility: hidden;}
</style>
"""
st.markdown(hacker_style, unsafe_allow_html=True)

# ================= 1. شاشة قفل النظام بباسورد =================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🔒 نظام تصفية الجروب // ACCESS LOCKED</h1>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        pwd = st.text_input("🔑 أدخل كلمة المرور للدخول للنظام:", type="password")
        if st.button("🔓 فتح النظام"):
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة!")
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

st.markdown("<h1 style='text-align: center;'>[ 👨‍💻 نظام تصفية الجروب // ULTIMATE CONTROL PANEL ]</h1>", unsafe_allow_html=True)
st.divider()

# ================= دوال الاتصال بتليجرام =================
async def scan_groups(groups, allowed_users, allowed_phones):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        st.error("⚠️ ملف الجلسة (my_session.session) غير صالح!")
        await client.disconnect()
        return [], {}

    results = []
    total_members = 0
    matched_users = set()

    for link in groups:
        clean_link = link.strip()
        if not clean_link:
            continue
        try:
            entity = await client.get_entity(clean_link)
            group_title = getattr(entity, 'title', clean_link)

            participants = await client.get_participants(entity)
            for user in participants:
                if user.bot or user.deleted or user.is_self:
                    continue
                total_members += 1

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
                        "group_link": clean_link,
                        "user_id": user.id,
                        "الاسم على تليجرام": user.first_name or "بدون اسم",
                        "اليوزر": f"@{username}" if username else "لا يوجد",
                        "رقم الهاتف": user.phone if user.phone else "مخفي",
                        "حساب وهمي": (username is None and user_phone is None)
                    })
        except Exception as e:
            st.error(f"❌ خطأ في الجروب ({clean_link}): {e}")

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
            status_box.success(f"⚡ {action_type}: {row['الاسم على تليجرام']} ({idx+1}/{total_targets})")
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
            st.warning(f"⚠️ فشل مع {row['الاسم على تليجرام']}: {e}")
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
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    new_links = {}
    for link in groups:
        clean_link = link.strip()
        if clean_link:
            try:
                res = await client(ExportChatInviteRequest(clean_link))
                new_links[clean_link] = res.link
            except Exception as e:
                st.error(f"فشل تجديد رابط {clean_link}: {e}")
    await client.disconnect()
    return new_links

# ================= الصفحة 1: الصفحة الرئيسية =================
if st.session_state.page == "home":
    col1, col2 = st.columns(2)
    with col1:
        groups_input = st.text_area("🔗 أدخل رابط الجروب (أو عدة روابط، كل رابط في سطر):", height=110, placeholder="https://t.me")
        whitelist_users = st.text_input("🛡️ استثناء يوزرات يدوي (افصل بينهم بفاصلة):", placeholder="@Mohammed_Tharwet, @ahmed_ali")
        whitelist_phones = st.text_area("📱 استثناء أرقام هواتف يدوي (كل رقم في سطر):", height=90, placeholder="01004960925\n01204643545")
    with col2:
        uploaded_file = st.file_uploader("📂 ارفع ملف الفورم (CSV أو XLSX - اختياري لو دخلت بيانات يدوي):", type=['csv', 'xlsx'])
        
        # زرار الفحص هنا مباشر وواضح قدامك علطول
        st.write("")
        start_btn = st.button("🚀 بدء الفحص واستخراج الأهداف")

        with st.expander("📢 إرسال رسالة تنبيه في الجروب قبل التصفية"):
            warn_msg = st.text_area("نص الرسالة:", value="⚠️ تنبيه هام: جاري تصفية الجروب تلقائياً الآن وحذف أي حساب غير مسجل في فورم الدفعة.")
            if st.button("📨 إرسال التحذير الآن"):
                if groups_input.strip():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(send_warning_msg(groups_input.strip().split('\n'), warn_msg))
                    st.success("✅ تم إرسال رسالة التحذير للجروب بنجاح!")
                else:
                    st.warning("⚠️ اكتب رابط الجروب فوق الأول!")

    if start_btn:
        if not groups_input.strip():
            st.warning("⚠️ برجاء إدخال رابط جروب واحد على الأقل!")
        elif not uploaded_file and not whitelist_users.strip() and not whitelist_phones.strip():
            st.warning("⚠️ برجاء رفع ملف الفورم أو كتابة يوزرات/أرقام مستثناة على الأقل!")
        else:

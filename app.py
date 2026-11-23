import asyncio
from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from telethon import TelegramClient
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChatBannedRights

# ================= إعدادات الأمان والمفاتيح =================
try:
    API_ID = int(st.secrets["API_ID"])
    API_HASH = str(st.secrets["API_HASH"])
    APP_PASSWORD = str(st.secrets.get("APP_PASSWORD", "12345"))
except Exception:
    API_ID = 0
    API_HASH = ""
    APP_PASSWORD = "12345"

st.set_page_config(page_title="تصفية الجروب | Ultimate Control Panel", page_icon="👨‍💻", layout="wide")

# ================= تصميم الهاكر + Matrix Rain =================
hacker_style = """
<style>
    @import url('https://googleapis.com');
    .stApp {
        background-color: #020502;
        color: #00FF41;
        font-family: 'Cairo', 'Fira Code', monospace;
    }
    h1, h2, h3, label, .stMarkdown p, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        color: #00FF41 !important;
        text-shadow: 0 0 8px rgba(0, 255, 65, 0.5);
        font-family: 'Cairo', monospace !important;
    }
    .stTextArea textarea, .stTextInput input, [data-testid="stFileUploader"] {
        background-color: #071207 !important;
        color: #00FF41 !important;
        border: 1px solid #00FF41 !important;
    }
    .stButton > button {
        background-color: #002609 !important;
        color: #00FF41 !important;
        border: 2px solid #00FF41 !important;
        font-weight: bold !important;
        font-size: 18px !important;
        padding: 10px !important;
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.4);
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #00FF41 !important;
        color: #000000 !important;
    }
    header {visibility: hidden;}
    iframe[title="streamlit_components_v1.html_v1"] {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 0;
        opacity: 0.15;
        pointer-events: none;
    }
    .block-container {
        position: relative;
        z-index: 1;
    }
</style>
"""
st.markdown(hacker_style, unsafe_allow_html=True)

matrix_canvas = """
<canvas id="matrix"></canvas>
<script>
const canvas = document.getElementById('matrix');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;
const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンABCDEFGHIJKLMNOPQRSTUVWXYZ';
const fontSize = 14;
const columns = canvas.width / fontSize;
const drops = Array(Math.floor(columns)).fill(1);
function draw() {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.06)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#00FF41';
    ctx.font = fontSize + 'px monospace';
    for (let i = 0; i < drops.length; i++) {
        const text = chars.charAt(Math.floor(Math.random() * chars.length));
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
        drops[i]++;
    }
}
setInterval(draw, 35);
</script>
"""
components.html(matrix_canvas, height=0)

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
for k, v in [("scan_results", []), ("stats", {}), ("kicked_report", []), ("scanned_groups", []), ("dup_info", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("<h1 style='text-align: center;'>[ 👨‍💻 نظام تصفية الجروب // ULTIMATE CONTROL PANEL ]</h1>", unsafe_allow_html=True)
st.divider()

# ================= دوال الاتصال بتليجرام =================
async def scan_groups(groups, allowed_users, allowed_phones):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        st.error("⚠️ ملف الجلسة (my_session.session) غير صالح أو غير موجود!")
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
            st.error(f"❌ تعذر فحص الجروب ({clean_link}) -> السبب: {e}")

    await client.disconnect()
    stats = {
        "total": total_members,
        "registered": total_members - len(results),
        "to_kick": len(results),
        "not_joined": max(0, len(allowed_users) - len(matched_users))
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
        mins, secs = divmod((total_targets - idx) * 3, 60)
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

# ================= الواجهة الرئيسية =================
col1, col2 = st.columns(2)
with col1:
    groups_input = st.text_area("🔗 أدخل رابط الجروب (كل رابط في سطر):", height=110, placeholder="https://t.me")
    whitelist_users = st.text_input("🛡️ استثناء يوزرات يدوي (افصل بفاصلة):", placeholder="@Mohammed_Tharwet")
    whitelist_phones = st.text_area("📱 استثناء أرقام هواتف يدوي (كل رقم في سطر):", height=90, placeholder="01004960925")

with col2:
    uploaded_file = st.file_uploader("📂 ارفع ملف الفورم (CSV أو XLSX - اختياري):", type=['csv', 'xlsx'])
    st.write("")

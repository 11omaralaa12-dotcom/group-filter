import asyncio
from datetime import datetime
import pandas as pd
import streamlit as st
from telethon import TelegramClient
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChatBannedRights

try:
    API_ID = int(st.secrets["API_ID"])
    API_HASH = st.secrets["API_HASH"]
    APP_PASSWORD = str(st.secrets.get("APP_PASSWORD", "12345"))
except Exception:
    API_ID = 0
    API_HASH = ""
    APP_PASSWORD = "12345"

st.set_page_config(page_title="تصفية الجروب", page_icon="👨‍💻", layout="wide")

hacker_style = """
<style>
    @import url('https://googleapis.com');
    .stApp {
        background-color: #020502;
        background-image: radial-gradient(#003b0f 1px, transparent 1px);
        background-size: 24px 24px;
        color: #00FF41;
        font-family: 'Cairo', monospace;
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
        color: #000 !important;
    }
    header {visibility: hidden;}
</style>
"""
st.markdown(hacker_style, unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🔒 نظام تصفية الجروب // ACCESS LOCKED</h1>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        pwd = st.text_input("🔑 أدخل كلمة المرور:", type="password")
        if st.button("🔓 فتح النظام"):
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة!")
    st.stop()

for k, v in [("page", "home"), ("scan_results", []), ("stats", {}), ("kicked_report", []), ("scanned_groups", []), ("dup_info", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("<h1 style='text-align: center;'>[ 👨‍💻 نظام تصفية الجروب // CONTROL PANEL ]</h1>", unsafe_allow_html=True)
st.divider()

async def scan_groups(groups, allowed_users, allowed_phones):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        st.error("⚠️ ملف الجلسة غير صالح!")
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
        timer_box.caption(f"⏱️ الوقت المتبقي: {mins} دقيقة و {secs} ثانية")
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
        if link.strip():
            try:
                await client.send_message(link.strip(), msg_text)
            except Exception as e:
                st.error(f"فشل الإرسال: {e}")
    await client.disconnect()

async def revoke_invite_links(groups):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    new_links = {}
    for link in groups:
        if link.strip():
            try:
                res = await client(ExportChatInviteRequest(link.strip()))
                new_links[link.strip()] = res.link
            except Exception as e:
                st.error(f"فشل تجديد الرابط: {e}")
    await client.disconnect()
    return new_links

if st.session_state.page == "home":
    col1, col2 = st.columns(2)
    with col1:
        groups_input = st.text_area("🔗 أدخل رابط الجروب (كل رابط في سطر):", height=110)
        whitelist_users = st.text_input("🛡️ استثناء يوزرات يدوي (افصل بفاصلة):")
        whitelist_phones = st.text_area("📱 استثناء أرقام هواتف يدوي (كل رقم في سطر):", height=90)
    with col2:
        uploaded_file = st.file_uploader("📂 ارفع ملف الفورم (CSV أو XLSX - اختياري):", type=['csv', 'xlsx'])
        st.write("")
        start_btn = st.button("🚀 بدء الفحص واستخراج الأهداف")
        with st.expander("📢 إرسال رسالة تنبيه في الجروب قبل التصفية"):
            warn_msg = st.text_area("نص الرسالة:", value="⚠️ تنبيه هام: جاري تصفية الجروب تلقائياً الآن وحذف أي حساب غير مسجل.")
            if st.button("📨 إرسال التحذير الآن"):
                if groups_input.strip():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(send_warning_msg(groups_input.strip().split('\n'), warn_msg))
                    st.success("✅ تم إرسال التحذير!")
                else:
                    st.warning("⚠️ اكتب رابط الجروب أولاً!")

    if start_btn:
        if not groups_input.strip():
            st.warning("⚠️ أدخل رابط جروب واحد على الأقل!")
        elif not uploaded_file and not whitelist_users.strip() and not whitelist_phones.strip():
            st.warning("⚠️ ارفع ملف أو اكتب استثناءات أولاً!")
        else:
            allowed_users = set()
            allowed_phones = set()
            st.session_state.dup_info = ""

            if uploaded_file is not None:
                df = pd.read_csv(uploaded_file, encoding='utf-8') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                total_rows = len(df)
                for col in df.columns:
                    for val in df[col].dropna().astype(str):
                        val = val.strip()
                        if val.startswith('@') or (val.replace('_', '').isalnum() and not val.isdigit() and len(val) >= 4):
                            allowed_users.add(val.replace('@', '').lower())
                        clean_p = ''.join(filter(str.isdigit, val))
                        if len(clean_p) >= 10 and not val.startswith('http'):
                            allowed_phones.add(clean_p[-10:])
                unique_entries = max(len(allowed_users), len(allowed_phones))

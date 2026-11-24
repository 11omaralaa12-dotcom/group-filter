import asyncio
import importlib
import os
import random
import re
import time
from datetime import datetime

import pandas as pd
import streamlit as st
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChatBannedRights

# ================= إعدادات الصفحة والتهيئة =================
st.set_page_config(
    page_title="تصفية الجروب | Ultimate Control Panel",
    page_icon="👨‍💻",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= قراءة المفاتيح من secrets.toml =================
try:
    API_ID = int(st.secrets["API_ID"])
    API_HASH = str(st.secrets["API_HASH"])
    OWNER_PHONE = str(st.secrets["OWNER_PHONE"]).strip()
    ADMIN_USERNAME = str(st.secrets.get("ADMIN_USERNAME", "الأدمن")).strip()
except Exception:
    st.error("⚠️ خطأ في قراءة ملف `.streamlit/secrets.toml`. تأكد من إضافة API_ID و API_HASH و OWNER_PHONE.")
    st.stop()

# ================= تصميم الهاكر / Cyberpunk (RTL + Cairo + Glow) =================
hacker_css = """
<style>
    @import url('https://googleapis.com');

    /* اتجاه عربي كامل */
    html, body, [class*="css"], .stApp {
        direction: rtl;
        text-align: right;
        font-family: 'Cairo', 'Fira Code', sans-serif !important;
        background-color: #020502;
        background-image: radial-gradient(#003b0f 1px, transparent 1px);
        background-size: 24px 24px;
        color: #00FF41;
    }

    /* العناوين والنصوص المتوهجة */
    h1, h2, h3, h4, label, .stMarkdown p, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        color: #00FF41 !important;
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.6);
        font-family: 'Cairo', sans-serif !important;
    }

    /* حقول الإدخال */
    .stTextArea textarea, .stTextInput input, [data-testid="stFileUploader"] section {
        background-color: #061206 !important;
        color: #00FF41 !important;
        border: 1px solid #00FF41 !important;
        box-shadow: inset 0 0 8px rgba(0, 255, 65, 0.2);
        border-radius: 8px !important;
        direction: rtl;
    }

    /* الأزرار بتأثير النيون */
    .stButton > button {
        background-color: #002208 !important;
        color: #00FF41 !important;
        border: 2px solid #00FF41 !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        padding: 10px 16px !important;
        border-radius: 8px !important;
        box-shadow: 0 0 12px rgba(0, 255, 65, 0.4);
        width: 100%;
        transition: all 0.25s ease-in-out;
    }

    .stButton > button:hover {
        background-color: #00FF41 !important;
        color: #020502 !important;
        box-shadow: 0 0 25px #00FF41;
        transform: translateY(-2px);
    }

    /* الصناديق والبطاقات */
    .cyber-box {
        background-color: rgba(5, 18, 5, 0.85);
        border: 1px solid #00FF41;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.25);
        margin-bottom: 15px;
    }

    /* الجداول */
    [data-testid="stDataEditor"] {
        border: 1px solid #00FF41 !important;
        border-radius: 8px;
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.2);
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""
st.markdown(hacker_css, unsafe_allow_html=True)

# ================= دوال مساعدة لإدارة Asyncio =================
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ================= دوال التنظيف والاستخراج الذكي (Smart Parser) =================
def normalize_phone(phone_str):
    if not phone_str:
        return None
    digits = re.sub(r'\D', '', str(phone_str))
    if len(digits) >= 10:
        return digits[-10:]  # توحيد آخر 10 أرقام (مثال: 1001234567)
    return None

def normalize_username(user_str):
    if not user_str:
        return None
    clean = str(user_str).strip().lstrip('@').lower()
    if re.match(r'^[a-z0-9_]{4,32}$', clean):
        return clean
    return None

def extract_from_text_blob(text_blob, users_set, phones_set):
    # استخراج أرقام الهواتف المصرية والدولية المحتملة
    raw_phones = re.findall(r'(?:\+?20|0020|0)?1[0125]\d{8}', text_blob)
    for p in raw_phones:
        norm_p = normalize_phone(p)
        if norm_p:
            phones_set.add(norm_p)

    # استخراج اليوزرات سواء بعلامة @ أو روابط t.me
    raw_at_users = re.findall(r'(?:@|t\.me/)([a-zA-Z0-9_]{4,32})', text_blob)
    for u in raw_at_users:
        norm_u = normalize_username(u)
        if norm_u:
            users_set.add(norm_u)

def smart_parse_files(uploaded_files):
    allowed_users = set()
    allowed_phones = set()

    for file in uploaded_files:
        filename = file.name.lower()
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file, dtype=str).fillna('')
                full_text = " ".join(df.astype(str).values.flatten())
                extract_from_text_blob(full_text, allowed_users, allowed_phones)
                # فحص الخلايا الفردية لالتقاط اليوزرات المكتوبة بدون @
                for val in df.values.flatten():
                    val_str = str(val).strip()
                    if val_str and not val_str.isdigit() and ' ' not in val_str:
                        u = normalize_username(val_str)
                        if u and not u.startswith('http'):
                            allowed_users.add(u)

            elif filename.endswith(('.xlsx', '.xls')):
                excel_data = pd.read_excel(file, sheet_name=None, dtype=str)
                for _, df in excel_data.items():
                    df = df.fillna('')
                    full_text = " ".join(df.astype(str).values.flatten())
                    extract_from_text_blob(full_text, allowed_users, allowed_phones)
                    for val in df.values.flatten():
                        val_str = str(val).strip()
                        if val_str and not val_str.isdigit() and ' ' not in val_str:
                            u = normalize_username(val_str)
                            if u and not u.startswith('http'):
                                allowed_users.add(u)

            elif filename.endswith('.pdf'):
                pdfplumber = importlib.import_module('pdfplumber')
                with pdfplumber.open(file) as pdf:
                    pdf_text = ""
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            pdf_text += "\n" + extracted
                    extract_from_text_blob(pdf_text, allowed_users, allowed_phones)
                    # فحص الكلمات المنفصلة لالتقاط اليوزرات بدون @
                    for token in re.split(r'[\s,;|]+', pdf_text):
                        if not token.isdigit():
                            u = normalize_username(token)
                            if u and not u.startswith('http'):
                                allowed_users.add(u)

        except Exception as e:
            st.error(f"❌ خطأ أثناء قراءة الملف ({file.name}): {e}")

    return allowed_users, allowed_phones

# ================= دوال تليجرام (Telethon) =================
async def send_otp_to_saved_messages(otp_code):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return False, "ملف الجلسة (my_session.session) غير متصل أو غير صالح!"

    msg = (
        f"🔐 **رمز التحقق للدخول إلى لوحة تصفية الجروب**\n\n"
        f"الرمز السري الخاص بك هو: `{otp_code}`\n"
        f"⏱️ صالح لجلسة الدخول الحالية فقط."
    )
    await client.send_message('me', msg)
    await client.disconnect()
    return True, "تم إرسال الرمز بنجاح إلى الرسائل المحفوظة (Saved Messages) على تليجرام."

async def scan_telegram_groups(groups, allowed_users, allowed_phones):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        st.error("⚠️ ملف الجلسة (my_session.session) غير صالح!")
        await client.disconnect()
        return [], {}

    candidates = []
    total_scanned = 0
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
                total_scanned += 1

                username = user.username.lower() if user.username else None
                norm_phone = normalize_phone(user.phone) if user.phone else None

                in_users = (username in allowed_users) if username else False
                in_phones = (norm_phone in allowed_phones) if norm_phone else False

                if in_users:
                    matched_users.add(username)

                if not (in_users or in_phones):
                    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "بدون اسم"
                    candidates.append({
                        "حذف": True,
                        "الاسم على تليجرام": full_name,
                        "اليوزر": f"@{username}" if username else "لا يوجد",
                        "رقم الهاتف": user.phone if user.phone else "مخفي",
                        "الجروب": group_title,
                        "group_link": clean_link,
                        "user_id": user.id
                    })
        except Exception as e:
            st.warning(f"⚠️ خطأ أثناء مسح الجروب ({clean_link}): {e}")  
import asyncio
import pandas as pd
import streamlit as st # type: ignore
from streamlit.components.v1 import html # type: ignore
from telethon import TelegramClient
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights


try:
    API_ID = int(st.secrets["API_ID"])
    API_HASH = st.secrets["API_HASH"]
except Exception:
    API_ID = 0
    API_HASH = ""




st.set_page_config(page_title="تصفية الجروب", page_icon="👨‍💻", layout="wide")

hacker_style = """
<style>
    @import url('https://googleapis.com');

    /* خلفية سوداء بالكامل */
    .stApp {
        background-color: #020502;
        color: #00FF41;
        font-family: 'Cairo', 'Fira Code', monospace;
    }

    /* تنسيق العناوين بتوهج أخضر */
    h1, h2, h3, label, .stMarkdown p {
        color: #00FF41 !important;
        text-shadow: 0 0 8px rgba(0, 255, 65, 0.6);
        font-family: 'Cairo', monospace !important;
    }

    /* خانات الإدخال ورفع الملفات */
    .stTextArea textarea, .stTextInput input, [data-testid="stFileUploader"] {
        background-color: #071207 !important;
        color: #00FF41 !important;
        border: 1px solid #00FF41 !important;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
        border-radius: 6px;
    }

    /* الزراير بستايل التيرمينال */
    .stButton > button {
        background-color: #001a05 !important;
        color: #00FF41 !important;
        border: 2px solid #00FF41 !important;
        font-weight: bold !important;
        font-size: 16px !important;
        box-shadow: 0 0 12px rgba(0, 255, 65, 0.4);
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #00FF41 !important;
        color: #000000 !important;
        box-shadow: 0 0 25px #00FF41;
    }

    /* إخفاء شريط ستريمليت العلوي */
    header {visibility: hidden;}
    
    /* تثبيت شاشة أكواد الماتريكس في الخلفية */
    iframe[title="streamlit_components_v1.html_v1"] {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 0;
        opacity: 0.22;
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
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
            drops[i] = 0;
        }
        drops[i]++;
    }
}
setInterval(draw, 35);
</script>
"""
html(matrix_canvas, height=0)


if "page" not in st.session_state:
    st.session_state.page = "home"
if "scan_results" not in st.session_state:
    st.session_state.scan_results = []


st.markdown("<h1 style='text-align: center;'>[👨‍💻 نظام تصفية الجروب//GROUP FILTER]</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; opacity: 0.8;'>SYSTEM STATUS: ONLINE | ACCESS: ROOT ADMIN</p>", unsafe_allow_html=True)
st.divider()

# ================= دوال الاتصال بتليجرام =================
async def scan_groups(groups, allowed_users, allowed_phones):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        st.error("⚠️ خطأ: ملف الجلسة (my_session.session) غير صالح أو غير موجود!")
        await client.disconnect()
        return []

    results = []
    for link in groups:
        link = link.strip()
        if not link:
            continue
        try:
            entity = await client.get_entity(link)
            group_title = getattr(entity, 'title', link)
            participants = await client.get_participants(entity)

            for user in participants:
                if user.bot or user.deleted or user.is_self:
                    continue
                username = user.username.lower() if user.username else None
                user_phone = user.phone[-10:] if (user.phone and len(user.phone) >= 10) else None

                if not ((username in allowed_users) or (user_phone in allowed_phones)):
                    results.append({
                        "تحديد": True,
                        "الجروب": group_title,
                        "group_link": link,
                        "user_id": user.id,
                        "الاسم على تليجرام": user.first_name or "بدون اسم",
                        "اليوزر": f"@{username}" if username else "لا يوجد",
                        "رقم الهاتف": user.phone if user.phone else "مخفي"
                    })
        except Exception as e:
            st.error(f"❌ فشل اختراق/فحص الرابط ({link}): {e}")

    await client.disconnect()
    return results

async def execute_kick(selected_rows):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()
    kick_rights = ChatBannedRights(until_date=None, view_messages=True)
    unban_rights = ChatBannedRights(until_date=None, view_messages=False)

    progress = st.progress(0)
    status_box = st.empty()
    kicked = 0

    for idx, row in enumerate(selected_rows):
        try:
            await client(EditBannedRequest(row["group_link"], int(row["user_id"]), kick_rights))
            await client(EditBannedRequest(row["group_link"], int(row["user_id"]), unban_rights))
            kicked += 1
            status_box.success(f"⚡ تم طرد الهدف: {row['الاسم على تليجرام']} ({idx+1}/{len(selected_rows)})")
            await asyncio.sleep(3)
        except Exception as e:
            st.warning(f"⚠️ تعذر طرد {row['الاسم على تليجرام']}: {e}")
        progress.progress((idx + 1) / len(selected_rows))

    await client.disconnect()
    return kicked

# ================= الصفحة 1: الصفحة الرئيسية =================
if st.session_state.page == "home":
    col1, col2 = st.columns(2)
    
    with col1:
        groups_input = st.text_area(
            "🔗 أدخل رابط الجروب (أو عدة روابط، كل رابط في سطر):",
            height=150,
            placeholder="https://t.me\nhttps://t.me"
        )
    
    with col2:
        uploaded_file = st.file_uploader(
            "📂 ارفع ملف الإكسيل (CSV أو XLSX) الخاص بالفورم:",
            type=['csv', 'xlsx']
        )

    st.write("")
    if st.button("🚀 بدء الفحص واستخراج الأهداف"):
        if not uploaded_file or not groups_input.strip():
            st.warning("⚠️ برجاء إدخال رابط الجروب ورفع ملف البيانات أولاً!")
        else:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            else:
                df = pd.read_excel(uploaded_file)

            phone_series = df.iloc[:, 3]
            username_series = df.iloc[:, -1]

            allowed_users = set(username_series.dropna().astype(str).str.replace('@', '', regex=False).str.strip().str.lower())
            allowed_phones = set()
            for p in phone_series.dropna().astype(str):
                clean_p = ''.join(filter(str.isdigit, p))
                if len(clean_p) >= 10:
                    allowed_phones.add(clean_p[-10:])

            with st.spinner("⏳ جاري سحب قاعدة بيانات الأعضاء ومطابقتها..."):
                groups = groups_input.strip().split('\n')
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                st.session_state.scan_results = loop.run_until_complete(scan_groups(groups, allowed_users, allowed_phones))
                st.session_state.page = "results"
                st.rerun()

# ================= الصفحة 2: صفحة النتائج والمراجعة =================
elif st.session_state.page == "results":
    results = st.session_state.scan_results


    if len(results) == 0:
        st.success("✅ النظام نظيف 100%! جميع الأعضاء مسجلين في الفورم.")
    else:
        st.subheader(f"🎯 تم رصد ({len(results)}) حساب غير مسجل في الفورم:")
        st.caption("راجع القائمة: شيل علامة الصح (✔) من قدام أي شخص مش عايز تمسحه.")

        df_results = pd.DataFrame(results)
        edited_df = st.data_editor(
            df_results,
            column_config={
                "group_link": None,
                "user_id": None,
                "تحديد": st.column_config.CheckboxColumn("مسح؟", default=True)
            },
            disabled=["الجروب", "الاسم على تليجرام", "اليوزر", "رقم الهاتف"],
            use_container_width=True,
            hide_index=True
        )

        selected_to_kick = edited_df[edited_df["تحديد"] == True].to_dict('records')
        st.write(f"عدد الحسابات المحددة للمسح حالياً: **{len(selected_to_kick)}**")

        # الزرارين جنب بعض في الأسفل: واحد مسح وواحد رجوع
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button(f"🗑️ امسح المحددين ({len(selected_to_kick)})", key="kick_btn"):
                if len(selected_to_kick) == 0:
                    st.warning("⚠️ لم تقم بتحديد أي شخص للمسح!")
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    kicked_count = loop.run_until_complete(execute_kick(selected_to_kick))
                    st.success(f"🔥 تمت التصفية بنجاح! تم طرد {kicked_count} حساب.")
                    st.session_state.scan_results = []

        with btn_col2:
            if st.button("🔙 رجوع للصفحة الرئيسية", key="bottom_back"):
                st.session_state.page = "home"
                st.session_state.scan_results = []
                st.rerun()

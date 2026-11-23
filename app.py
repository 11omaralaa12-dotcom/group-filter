import asyncio
import pandas as pd
import streamlit as st
from telethon import TelegramClient
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights

# قراءة المفاتيح من إعدادات السيرفر
API_ID = int(st.secrets["API_ID"])
API_HASH = str(st.secrets["API_HASH"])

st.set_page_config(page_title="منظف جروبات تليجرام", page_icon="🧹", layout="wide")
st.title("🧹 أداة تنظيف جروبات تليجرام الذكية")
st.markdown("ارفع ملف ردود الفورم، وحط روابط الجروبات، واختار بين **المعاينة** أو **الطرد الفعلي**.")

# 1. رفع ملف الفورم
uploaded_file = st.file_uploader("1️⃣ ارفع ملف ردود الفورم (CSV أو Excel)", type=['csv', 'xlsx'])

# 2. إدخال روابط الجروبات
groups_input = st.text_area(
    "2️⃣ اكتب روابط أو يوزرات الجروبات (كل جروب في سطر لوحده):",
    placeholder="https://t.me"
)

# 3. اختيار وضع التشغيل
mode = st.radio(
    "3️⃣ اختار وضع التشغيل:",
    ["🔍 معاينة فقط (عرض المرشحين للطرد بدون حذف)", "🚨 تنفيذ الطرد الفعلي (حذف غير المسجلين فوراً)"]
)

async def process_groups(groups, allowed_users, allowed_phones, is_dry_run):
    client = TelegramClient('my_session', API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        st.error("⚠️ الجلسة غير مسجلة أو منتهية!")
        await client.disconnect()
        return

    kick_rights = ChatBannedRights(until_date=None, view_messages=True)

    for link in groups:
        link = link.strip()
        if not link:
            continue

        st.subheader(f"📌 الجروب: {link}")
        try:
            participants = await client.get_participants(link)
            st.info(f"إجمالي الأعضاء الحاليين: **{len(participants)}** عضو")
        except Exception as e:
            st.error(f"فشل الدخول للجروب ({link}): {e}")
            continue

        candidates = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        to_kick = []
        for user in participants:
            if user.bot or user.deleted or user.is_self:
                continue
            username = user.username.lower() if user.username else None
            user_phone = user.phone[-10:] if (user.phone and len(user.phone) >= 10) else None

            if not ((username in allowed_users) or (user_phone in allowed_phones)):
                to_kick.append((user, username))

        if not to_kick:
            st.success("✅ الجروب نضيف تماماً! كل الأعضاء مسجلين في الفورم.")
            continue

        for idx, (user, username) in enumerate(to_kick):
            status = "مرشح للطرد (معاينة)"
            if not is_dry_run:
                try:
                    await client(EditBannedRequest(link, user, kick_rights))
                    status = "✅ تم الطرد"
                    status_text.text(f"جاري طرد: {user.first_name} ({idx+1}/{len(to_kick)})...")
                    await asyncio.sleep(3)
                except Exception as e:
                    status = f"❌ فشل ({e})"

            candidates.append({
                "الاسم": user.first_name or "بدون اسم",
                "اليوزر": f"@{username}" if username else "لا يوجد",
                "رقم الهاتف": user.phone if user.phone else "مخفي",
                "الحالة": status
            })
            progress_bar.progress((idx + 1) / len(to_kick))

        st.write(f"العدد: **{len(candidates)}** شخص")
        st.dataframe(pd.DataFrame(candidates), use_container_width=True)

    await client.disconnect()
    st.success("🎉 تمت العملية بنجاح!")

if st.button("🚀 ابدأ الفحص والتنظيف", type="primary"):
    if not uploaded_file:
        st.warning("من فضلك ارفع ملف الفورم الأول!")
    elif not groups_input.strip():
        st.warning("من فضلك اكتب رابط جروب واحد على الأقل!")
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

        st.success(f"تم تحميل الفورم: **{len(allowed_users)}** يوزر و **{len(allowed_phones)}** رقم هاتف.")
        
        groups = groups_input.strip().split('\n')
        is_dry_run = "معاينة" in mode

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_groups(groups, allowed_users, allowed_phones, is_dry_run))

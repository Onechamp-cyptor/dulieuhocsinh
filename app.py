import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI

# ====== 1. ĐỌC SECRETS ======
creds_dict = dict(st.secrets["google_service_account"])
openai_key = st.secrets["OPENAI_API_KEY"]

# ====== 2. KẾT NỐI GOOGLE SHEETS ======
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client_gs = gspread.authorize(creds)

# Thay bằng ID Google Sheet của bạn
SHEET_ID = "ID_GOOGLE_SHEET"
sheet = client_gs.open_by_key(SHEET_ID).sheet1

# ====== 3. KẾT NỐI OPENAI ======
client_ai = OpenAI(api_key=openai_key)

def generate_comment(student, week):
    prompt = f"""
    Đây là dữ liệu tuần {week} của học sinh:
    {student}

    Hãy viết báo cáo ngắn gọn gửi cho phụ huynh gồm:
    - Các môn học tốt
    - Các môn còn hạn chế
    - Lời khuyên ngắn gọn để phụ huynh hỗ trợ con
    """
    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )
    return response.choices[0].message.content

def get_student_data(student_id, week):
    records = sheet.get_all_records()
    student_records = [r for r in records if str(r.get("Mã HS", "")).strip() == str(student_id).strip()]
    if not student_records:
        return None
    for r in student_records:
        if str(r.get("Tuần", "")).strip() == str(week).strip():
            return r
    return None

# ====== 4. GIAO DIỆN STREAMLIT ======
st.title("📊 Hệ thống nhận xét học sinh (AI + Google Sheets)")

student_id = st.text_input("Nhập Mã HS:")
week = st.text_input("Nhập tuần (ví dụ: 1, 2, 3):")

if st.button("Xem kết quả"):
    student = get_student_data(student_id, week)
    if student:
        comment = generate_comment(student, week)
        st.success(f"✅ Nhận xét tuần {week}:")
        st.write(comment)
    else:
        st.error("❌ Không tìm thấy dữ liệu cho học sinh/tuần này.")

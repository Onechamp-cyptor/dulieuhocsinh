import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI

# =========================
# 1. KẾT NỐI GOOGLE SHEETS
# =========================
# Lấy key service account từ Secrets
creds_dict = dict(st.secrets["google_service_account"])

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client_gs = gspread.authorize(creds)

# Thay bằng ID Google Sheet của bạn
SHEET_ID = "1nMhTwPKYU_Ik1SFUZKaeZTLUXlqcWk2cC4kahQ_RKpg"
sheet = client_gs.open_by_key(SHEET_ID).sheet1
records = sheet.get_all_records()

# =========================
# 2. KẾT NỐI OPENAI
# =========================
openai_key = st.secrets["OPENAI_API_KEY"]
client_ai = OpenAI(api_key=openai_key)

def generate_comment(student, week):
    """Sinh nhận xét từ dữ liệu học sinh"""
    prompt = f"""
    Đây là dữ liệu tuần {week} của học sinh:
    {student}

    Hãy viết báo cáo ngắn gọn gửi cho phụ huynh gồm:
    - Các môn học tốt
    - Các môn còn hạn chế
    - Lời khuyên ngắn gọn để phụ huynh hỗ trợ con
    """
    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",   # có thể thay bằng "gpt-4o" nếu cần
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )
    return response.choices[0].message.content

def get_student_data(student_id, week):
    """Tìm dữ liệu học sinh theo ID + tuần"""
    student_records = [r for r in records if str(r.get("Mã HS", "")).strip() == str(student_id).strip()]
    
    if not student_records:
        return None
    
    if 1 <= int(week) <= len(student_records):
        return student_records[int(week) - 1]
    else:
        return None

# =========================
# 3. GIAO DIỆN STREAMLIT
# =========================
st.image("logo.png", caption="Hệ thống nhận xét học sinh", use_column_width=True)
st.title("📊 Hệ thống nhận xét học sinh (AI + Google Sheets)")

uploaded_file = st.file_uploader("📷 Tải ảnh học sinh", type=["png", "jpg", "jpeg"])
if uploaded_file is not None:
    st.image(uploaded_file, caption="Ảnh học sinh", use_column_width=True)

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

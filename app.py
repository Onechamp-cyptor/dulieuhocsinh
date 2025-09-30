import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import openai
import pandas as pd

# --- Kết nối Google Sheets ---
st.title("📘 Quản lý điểm học sinh bằng AI")

# Lấy Google Service Account từ secrets
creds_dict = dict(st.secrets["google_service_account"])
creds = Credentials.from_service_account_info(creds_dict)
client_gs = gspread.authorize(creds)

# Nhập SHEET_ID (Google Sheets URL dạng: https://docs.google.com/spreadsheets/d/xxxxxxx/edit)
SHEET_ID = "1nMhTwPKYU_1k1SFUZKaeZTLlXlqcWk2cC4kahQ_Kpg"
sheet = client_gs.open_by_key(SHEET_ID).sheet1

# Đọc dữ liệu thành DataFrame
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.subheader("📊 Bảng điểm hiện tại")
st.dataframe(df)

# --- Chức năng tra cứu ---
st.subheader("🔍 Tra cứu điểm học sinh")
student_name = st.text_input("Nhập tên học sinh:")

if student_name:
    results = df[df["Họ tên"].str.contains(student_name, case=False)]
    if not results.empty:
        st.write("✅ Kết quả tìm thấy:")
        st.dataframe(results)
    else:
        st.warning("Không tìm thấy học sinh này.")

# --- Tích hợp AI để tư vấn ---
st.subheader("🤖 Hỏi AI về kết quả học tập")

question = st.text_area("Nhập câu hỏi (ví dụ: Nhận xét về Nguyễn Văn A):")

if st.button("Hỏi AI"):
    if not question:
        st.warning("Bạn cần nhập câu hỏi.")
    else:
        openai.api_key = st.secrets["OPENAI_API_KEY"]

        # Tạo prompt từ dữ liệu
        context = df.to_string(index=False)

        prompt = f"""
        Đây là bảng điểm của học sinh:
        {context}

        Câu hỏi: {question}

        Hãy trả lời rõ ràng, dễ hiểu cho phụ huynh.
        """

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Bạn là một cố vấn học tập."},
                      {"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )

        answer = response.choices[0].message["content"]
        st.success("💡 Trả lời của AI:")
        st.write(answer)

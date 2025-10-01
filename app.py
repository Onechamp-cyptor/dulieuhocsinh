import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai

# ---------------------------
# Cấu hình Streamlit
# ---------------------------
st.set_page_config(page_title="Quản lý điểm học sinh", page_icon="📘", layout="wide")
st.title("📘 Quản lý điểm học sinh (Google Sheets + AI)")

# ---------------------------
# Hàm tải dữ liệu Google Sheets
# ---------------------------
def load_data():
    try:
        creds_dict = dict(st.secrets["google_service_account"])
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(creds)
        SHEET_ID = st.secrets["sheets"]["sheet_id"]
        sheet = client.open_by_key(SHEET_ID).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return sheet, df
    except Exception as e:
        st.error("❌ Lỗi tải dữ liệu Google Sheets")
        st.exception(e)
        return None, None

# ---------------------------
# Hàm AI nhận xét học sinh
# ---------------------------
def ai_nhan_xet(thong_tin):
    try:
        openai.api_key = st.secrets["openai"]["api_key"]

        prompt = f"""
        Bạn là giáo viên chủ nhiệm. Đây là dữ liệu chi tiết của học sinh:

        {thong_tin.to_dict(orient="records")}

        Hãy viết nhận xét gửi phụ huynh, trong đó:
        - Phân tích kết quả học tập (ưu điểm và hạn chế).
        - Nhận xét mức độ tham gia phong trào, vệ sinh lớp, phát biểu xây dựng bài... (dựa vào các cột có dấu tick ✓ hoặc TRUE/FALSE).
        - Đưa ra lời khuyên cụ thể để giúp học sinh tiến bộ hơn.
        """

        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là một giáo viên chủ nhiệm tận tâm, viết nhận xét rõ ràng, thân thiện và chi tiết."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400
        )
        return resp.choices[0].message.content

    except Exception as e:
        st.error("❌ Lỗi khi gọi OpenAI API")
        st.exception(e)
        return None

# ---------------------------
# Giao diện chính
# ---------------------------
sheet, df = load_data()

if df is not None:
    st.subheader("🔍 Tra cứu học sinh")
    student_id = st.text_input("Nhập ID")
    student_name = st.text_input("Hoặc nhập tên")

    results = None
    if student_id:
        if "ID" in df.columns:
            results = df[df["ID"].astype(str) == student_id]
        else:
            st.warning("⚠️ Google Sheets chưa có cột 'ID'")
    elif student_name:
        if "Họ tên" in df.columns:
            results = df[df["Họ tên"].str.contains(student_name, case=False)]
        else:
            st.warning("⚠️ Google Sheets chưa có cột 'Họ tên'")

    if results is not None and not results.empty:
        st.dataframe(results)
        if st.button("📌 Nhận xét phụ huynh"):
            nhan_xet = ai_nhan_xet(results)
            if nhan_xet:
                st.write(nhan_xet)
    else:
        st.info("⚠️ Không tìm thấy học sinh")

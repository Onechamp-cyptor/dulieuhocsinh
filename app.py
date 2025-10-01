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

# ---------------------------
# Hàm AI nhận xét học sinh
# ---------------------------
def ai_nhan_xet(thong_tin_hoc_sinh):
    openai.api_key = st.secrets["openai"]["api_key"]

    prompt = f"""
    Bạn là giáo viên chủ nhiệm. Đây là dữ liệu điểm của một học sinh:

    {thong_tin_hoc_sinh.to_dict(orient="records")}

    Hãy viết một đoạn nhận xét gửi phụ huynh: nêu rõ ưu điểm, hạn chế, và lời khuyên để cải thiện kết quả học tập.
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # hoặc gpt-4o nếu bạn muốn
            messages=[
                {"role": "system", "content": "Bạn là một giáo viên tâm huyết."},
                {"role": "user", "content": prompt}
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai

st.set_page_config(page_title="Quản lý học sinh", page_icon="📘", layout="wide")
st.title("📘 Quản lý điểm học sinh")

def load_data():
    creds_dict = dict(st.secrets["google_service_account"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    SHEET_ID = st.secrets["sheets"]["sheet_id"]
    sheet = client.open_by_key(SHEET_ID).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return sheet, df

def ai_nhan_xet(thong_tin):
    openai.api_key = st.secrets["openai"]["api_key"]
    prompt = f"Hãy viết nhận xét gửi phụ huynh dựa trên dữ liệu: {thong_tin.to_dict(orient='records')}"
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Bạn là giáo viên"},
                  {"role": "user", "content": prompt}],
        max_tokens=300
    )
    return resp.choices[0].message["content"]

try:
    if st.button("🔄 Làm mới dữ liệu"):
        sheet, df = load_data()
        st.dataframe(df)

        st.subheader("🔍 Tra cứu")
        student_id = st.text_input("Nhập ID")
        student_name = st.text_input("Hoặc nhập tên")

        results = None
        if student_id:
            results = df[df["ID"].astype(str) == student_id]
        elif student_name:
            results = df[df["Họ tên"].str.contains(student_name, case=False)]

        if results is not None and not results.empty:
            st.dataframe(results)
            if st.button("📌 Nhận xét phụ huynh"):
                st.write(ai_nhan_xet(results))
        else:
            st.info("⚠️ Không tìm thấy học sinh")

except Exception as e:
    st.error("❌ Lỗi kết nối Google Sheets")
    st.exception(e)


import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# =========================
# Cấu hình Streamlit
# =========================
st.set_page_config(page_title="Quản lý điểm học sinh", page_icon="📘", layout="wide")
st.title("📘 Quản lý điểm học sinh (Google Sheets + AI)")

# =========================
# Hàm tải dữ liệu Google Sheets
# =========================
@st.cache_data(ttl=300)
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

    SHEET_ID = st.secrets["sheet_id"]  # cần khai báo trong secrets.toml
    sheet = client.open_by_key(SHEET_ID).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    return df

df = load_data()

# =========================
# Menu chọn chức năng
# =========================
menu = st.sidebar.radio("Chọn chức năng", ["Tra cứu học sinh", "Thống kê lớp"])

# =========================
# TRA CỨU HỌC SINH
# =========================
if menu == "Tra cứu học sinh":
    st.header("🔍 Tra cứu học sinh")

    # Ô nhập ID và tên
    student_id = st.text_input("Nhập ID")
    student_name = st.text_input("Hoặc nhập tên")

    # Lấy danh sách tuần
    if "Tuần" in df.columns:
        week_list = sorted(
            set(
                str(x).strip() for x in df["Tuần"].dropna().unique() if str(x).strip() != ""
            ),
            key=lambda x: int(float(x)) if str(x).replace(".", "").isdigit() else x
        )
    else:
        week_list = []

    selected_week = st.selectbox("📅 Chọn tuần", week_list)

    # Lọc dữ liệu theo ID hoặc Tên
    if student_id:
        student_data = df[
            (df["ID"].astype(str) == str(student_id)) &
            (df["Tuần"].astype(str) == str(selected_week))
        ]
    elif student_name:
        student_data = df[
            (df["Họ tên"].str.lower().str.contains(student_name.lower())) &
            (df["Tuần"].astype(str) == str(selected_week))
        ]
    else:
        student_data = pd.DataFrame()

    # Hiển thị chi tiết tuần
    if not student_data.empty:
        st.subheader(f"📌 Chi tiết tuần {selected_week} (T2 → T7)")

        # Hiện đủ các ngày T2 → T7
        week_details = student_data.sort_values(by="Thứ", key=lambda x: x.str.extract(r'(\d+)').astype(float))
        st.dataframe(week_details, use_container_width=True)

        # Tính tổng điểm tuần
        st.subheader("📊 Tổng điểm tuần")
        total_points = week_details["Tổng điểm"].sum() if "Tổng điểm" in week_details else 0
        st.write(pd.DataFrame([{
            "ID": week_details.iloc[0]["ID"],
            "Họ tên": week_details.iloc[0]["Họ tên"],
            "Tổng điểm tuần": total_points
        }]))
    else:
        st.warning("⚠️ Không tìm thấy dữ liệu cho học sinh này.")

# =========================
# THỐNG KÊ LỚP
# =========================
elif menu == "Thống kê lớp":
    st.header("📊 Thống kê lớp")
    st.dataframe(df, use_container_width=True)

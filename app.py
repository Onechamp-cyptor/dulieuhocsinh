import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px

# ---------------------------
# Cấu hình Streamlit
# ---------------------------
st.set_page_config(page_title="Quản lý điểm học sinh", page_icon="📘", layout="wide")
st.title("📘 Quản lý điểm học sinh (Google Sheets + Dashboard)")

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

        # Chuẩn hoá tên cột
        df.columns = df.columns.str.strip()

        return df
    except Exception as e:
        st.error("❌ Lỗi tải dữ liệu Google Sheets")
        st.exception(e)
        return pd.DataFrame()

# ---------------------------
# Main App
# ---------------------------
df = load_data()

if df.empty:
    st.warning("⚠️ Không có dữ liệu từ Google Sheets. Vui lòng kiểm tra lại.")
else:
    # Menu chức năng
    chuc_nang = st.radio("🔧 Chọn chức năng", ["Tra cứu học sinh", "Thống kê lớp"])

    # ---------------------------
    # Tra cứu học sinh
    # ---------------------------
    if chuc_nang == "Tra cứu học sinh":
        st.subheader("🔍 Tra cứu học sinh")

        student_id = st.text_input("Nhập ID")
        student_name = st.text_input("Hoặc nhập tên")

        results = pd.DataFrame()
        if student_id:
            results = df[df["ID"].astype(str) == student_id]
        elif student_name:
            results = df[df["Họ tên"].str.contains(student_name, case=False, na=False)]

        if not results.empty:
            st.dataframe(results)
        else:
            st.info("⚠️ Không tìm thấy học sinh")

    # ---------------------------
    # Thống kê lớp
    # ---------------------------
    elif chuc_nang == "Thống kê lớp":
        st.subheader("📊 Thống kê lớp")

        # Điểm trung bình
        if "Tổng điểm tuần" in df.columns:
            try:
                df["Tổng điểm tuần"] = pd.to_numeric(df["Tổng điểm tuần"], errors="coerce").fillna(0)
                avg_score = df["Tổng điểm tuần"].mean()
                st.metric("Điểm trung bình cả lớp", round(avg_score, 2))
            except:
                st.warning("⚠️ Cột 'Tổng điểm tuần' có dữ liệu không hợp lệ")
        else:
            st.warning("⚠️ Không tìm thấy cột 'Tổng điểm tuần'")

        # Biểu đồ số lần vi phạm
        cols_tieu_chi = ["Đi học đúng giờ", "Đồng phục", "Thái độ học tập", "Trật tự", "Vệ sinh", "Phong trào"]
        violations = {}
        for col in cols_tieu_chi:
            if col in df.columns:
                violations[col] = (df[col] == "X").sum()

        if violations:
            fig = px.bar(
                x=list(violations.keys()),
                y=list(violations.values()),
                labels={"x": "Tiêu chí", "y": "Số lần vi phạm"},
                text=list(violations.values()),
                color=list(violations.keys())
            )
            fig.update_traces(textposition="outside")
            st.subheader("📌 Số lần vi phạm theo tiêu chí")
            st.plotly_chart(fig, use_container_width=True)

        # Top 4 học sinh điểm cao nhất
        if {"ID", "Họ tên", "Tổng điểm tuần"}.issubset(df.columns):
            try:
                top4 = (
                    df.groupby(["ID", "Họ tên"], as_index=False)["Tổng điểm tuần"]
                    .sum()  # cộng điểm các tuần
                    .sort_values(by="Tổng điểm tuần", ascending=False)
                    .head(4)
                )
                top4["Tổng điểm tuần"] = top4["Tổng điểm tuần"].astype(int)

                st.subheader("🏆 Top 4 học sinh điểm cao nhất (Tuyên dương)")
                st.dataframe(top4[["ID", "Họ tên", "Tổng điểm tuần"]])
            except Exception as e:
                st.error("❌ Lỗi khi xử lý dữ liệu xếp hạng")
                st.exception(e)
        else:
            st.warning("⚠️ Thiếu cột ID, Họ tên hoặc Tổng điểm tuần trong Google Sheets")


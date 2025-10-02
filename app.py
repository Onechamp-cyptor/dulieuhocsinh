import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import plotly.express as px

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
# Quy đổi tick / X sang mô tả
# ---------------------------
def xu_ly_du_lieu(thong_tin):
    df = thong_tin.copy()
    for col in df.columns:
        df[col] = df[col].replace({
            "✓": "Đạt (+20 điểm)",
            "X": "Chưa đạt (-30 điểm)",
            "": "Không ghi nhận",
            True: "Có (✓)",
            False: "Không"
        })
    return df

# ---------------------------
# Hàm AI nhận xét
# ---------------------------
def ai_nhan_xet(thong_tin):
    try:
        openai.api_key = st.secrets["openai"]["api_key"]

        data_quydoi = xu_ly_du_lieu(thong_tin)

        prompt = f"""
        Bạn là giáo viên chủ nhiệm. Đây là dữ liệu chi tiết của học sinh:

        {data_quydoi.to_dict(orient="records")}

        Hãy viết một nhận xét gửi phụ huynh, trong đó:
        - Nêu ưu điểm và hạn chế của học sinh.
        - Nhận xét về học tập, thái độ, kỷ luật, vệ sinh, tham gia phong trào...
        - Đưa ra lời khuyên cụ thể để giúp học sinh tiến bộ hơn.
        """

        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là giáo viên chủ nhiệm tận tâm, viết nhận xét rõ ràng, thân thiện và chi tiết."},
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
# Chạy app
# ---------------------------
sheet, df = load_data()

if df is not None:
    # Ép kiểu số cho cột Tổng điểm (tránh lỗi mean)
    if "Tổng điểm" in df.columns:
        df["Tổng điểm"] = pd.to_numeric(df["Tổng điểm"], errors="coerce").fillna(0)

    # Thanh chọn chức năng
    menu = st.radio("Chọn chức năng", ["🔍 Tra cứu học sinh", "📊 Thống kê lớp"])

    # ---------------- Tra cứu từng học sinh ----------------
    if menu == "🔍 Tra cứu học sinh":
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
                    st.success("✅ Nhận xét đã tạo:")
                    st.write(nhan_xet)
        else:
            st.info("⚠️ Không tìm thấy học sinh")

    # ---------------- Dashboard thống kê ----------------
    elif menu == "📊 Thống kê lớp":
        st.subheader("📊 Tổng quan lớp học")

        if "Tổng điểm" in df.columns:
            st.metric("Điểm trung bình cả lớp", round(df["Tổng điểm"].mean(), 2))

        # Đếm số lần vi phạm theo tiêu chí
        cols_tieuchi = ["Đi học đúng giờ", "Đồng phục", "Thái độ học tập", "Trật tự", "Vệ sinh", "Phong trào"]
        df_long = df.melt(id_vars=["Họ tên"], value_vars=cols_tieuchi, var_name="Tiêu chí", value_name="Kết quả")
        df_vi_pham = df_long[df_long["Kết quả"] == "X"].groupby("Tiêu chí").size().reset_index(name="Số lần vi phạm")

        st.subheader("📌 Số lần vi phạm theo tiêu chí")
        if not df_vi_pham.empty:
            fig = px.bar(df_vi_pham, x="Tiêu chí", y="Số lần vi phạm", color="Tiêu chí", text="Số lần vi phạm")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("✅ Không có vi phạm nào!")

        # Top 4 học sinh điểm cao nhất
        st.subheader("🏆 Top 4 học sinh điểm cao nhất (Tuyên dương)")

        if "Họ tên" in df.columns and "Tổng điểm" in df.columns:
            top4 = df.groupby("Họ tên", as_index=False)["Tổng điểm"].sum().sort_values(by="Tổng điểm", ascending=False).head(4)
            st.table(top4)
        else:
            st.warning("⚠️ Thiếu cột 'Họ tên' hoặc 'Tổng điểm'")

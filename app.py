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
# Hàm AI nhận xét học sinh
# ---------------------------
def ai_nhan_xet(thong_tin):
    try:
        openai.api_key = st.secrets["openai"]["api_key"]

        prompt = f"""
        Bạn là giáo viên chủ nhiệm. Đây là dữ liệu chi tiết của học sinh:

        {thong_tin.to_dict(orient="records")}

        Hãy viết một nhận xét gửi phụ huynh, trong đó:
        - Nêu ưu điểm và hạn chế của học sinh.
        - Nhận xét về học tập, thái độ, kỷ luật, vệ sinh, tham gia phong trào...
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
    menu = st.radio("Chọn chức năng", ["🔍 Tra cứu học sinh", "📊 Thống kê lớp"])

    # ---------------------------
    # Tra cứu học sinh
    # ---------------------------
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

    # ---------------------------
    # Dashboard lớp
    # ---------------------------
    elif menu == "📊 Thống kê lớp":
        st.header("📊 Thống kê tổng hợp lớp")

        if "Tổng điểm tuần" in df.columns:
            df["Tổng điểm tuần"] = pd.to_numeric(df["Tổng điểm tuần"], errors="coerce").fillna(0)

            # Điểm trung bình
            st.metric("Điểm trung bình cả lớp", round(df["Tổng điểm tuần"].mean(), 2))

            # Biểu đồ vi phạm theo tiêu chí
            vi_pham = {}
            for col in ["Đi học đúng giờ", "Đồng phục", "Thái độ học tập", "Trật tự", "Vệ sinh", "Phong trào"]:
                if col in df.columns:
                    vi_pham[col] = (df[col] == "X").sum()

            if vi_pham:
                vi_pham_df = pd.DataFrame(list(vi_pham.items()), columns=["Tiêu chí", "Số lần vi phạm"])
                fig = px.bar(vi_pham_df, x="Tiêu chí", y="Số lần vi phạm", color="Tiêu chí", text="Số lần vi phạm")
                st.subheader("📌 Số lần vi phạm theo tiêu chí")
                st.plotly_chart(fig, use_container_width=True)

            # Top 4 học sinh điểm cao nhất
            top4 = (
                df.groupby(["ID", "Họ tên"])["Tổng điểm tuần"]
                .sum()
                .reset_index()
                .sort_values(by="Tổng điểm tuần", ascending=False)
                .head(4)
            )
            top4["Tổng điểm tuần"] = top4["Tổng điểm tuần"].astype(int)
            st.subheader("🏆 Top 4 học sinh điểm cao nhất (Tuyên dương)")
            st.table(top4[["ID", "Họ tên", "Tổng điểm tuần"]])
        else:
            st.error("⚠️ Google Sheets chưa có cột 'Tổng điểm tuần'")


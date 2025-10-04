import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import plotly.express as px
from fpdf import FPDF
import tempfile
import base64

# ---------------------------
# ⚙️ Cấu hình Streamlit
# ---------------------------
st.set_page_config(page_title="Tình hình học tập của học sinh", page_icon="📘", layout="wide")

# ---------------------------
# 🎨 CSS giao diện
# ---------------------------
st.markdown("""
    <style>
    div[data-testid="stAppViewContainer"] {
        background-color: #f9f9f9;
    }
    h1, h2, h3 {
        color: #4285F4;
        font-weight: bold;
    }
    section[data-testid="stSidebar"] {
        background-color: #f1f3f4;
    }
    div.stButton > button:first-child {
        background-color: #34A853;
        color: white;
        border-radius: 10px;
        font-size: 16px;
        font-weight: bold;
        border: none;
        padding: 8px 20px;
    }
    div.stButton > button:hover {
        background-color: #0F9D58;
        color: white;
    }
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        border: 1px solid #dadce0;
        padding: 10px;
        background-color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📘 Tình hình học tập của học sinh (Google Sheets + AI)")

# ---------------------------
# 📊 Hàm tải dữ liệu Google Sheets
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

        data = sheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])

        df = df[df.apply(lambda row: not all(str(x).strip() == "" for x in row), axis=1)]

        if {"ID", "Họ tên"}.issubset(df.columns):
            df["ID"] = df["ID"].replace("", None)
            df["Họ tên"] = df["Họ tên"].replace("", None)
            df[["ID", "Họ tên"]] = df[["ID", "Họ tên"]].ffill()

        df = df.replace(["None", "nan", None], "")
        return sheet, df
    except Exception as e:
        st.error("❌ Lỗi tải dữ liệu Google Sheets")
        st.exception(e)
        return None, None

# ---------------------------
# 🤖 Hàm AI nhận xét học sinh
# ---------------------------
def ai_nhan_xet(thong_tin):
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        prompt = f"""
        Bạn là giáo viên chủ nhiệm. Đây là dữ liệu chi tiết của học sinh:

        {thong_tin.to_dict(orient="records")}

        Quy tắc phân tích:
        - Trên 8 điểm: học tập tốt
        - Từ 6 đến 8 điểm: có sự nỗ lực
        - Dưới 5 điểm: cần cố gắng thêm

        Hãy viết nhận xét thân thiện, có tính giáo dục và động viên.
        """

        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là giáo viên chủ nhiệm tận tâm, viết nhận xét ngắn gọn, truyền cảm hứng."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        return resp.choices[0].message.content
    except Exception as e:
        st.error("❌ Lỗi gọi OpenAI API")
        st.exception(e)
        return None

# ---------------------------
# 🧾 Hàm xuất PDF nhận xét
# ---------------------------
def export_pdf(ten_hs, nhan_xet):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt="NHẬN XÉT HỌC SINH", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 8, f"Họ và tên: {ten_hs}\n\nNhận xét:\n{nhan_xet}")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

# ---------------------------
# 🧭 Giao diện chính
# ---------------------------
sheet, df = load_data()

if df is not None:
    df["ID"] = df["ID"].astype(str)
    menu = st.sidebar.radio("📌 Chọn chức năng", ["Tra cứu học sinh", "Thống kê lớp"])

    # ------------------ TRA CỨU ------------------
    if menu == "Tra cứu học sinh":
        st.subheader("🔍 Tra cứu học sinh")
        student_id = st.text_input("Nhập ID học sinh")

        if student_id:
            results = df[df["ID"] == str(student_id)]
            if not results.empty:
                ten_hs = results["Họ tên"].iloc[0]
                st.info(f"✅ ID hợp lệ: {student_id} → Học sinh: **{ten_hs}**")

                # Nếu có cột Tháng thì cho chọn
                if "Tháng" in df.columns:
                    thang_list = sorted(df["Tháng"].unique())
                    selected_thang = st.selectbox("📅 Chọn tháng để xem kết quả", thang_list)
                    results = results[results["Tháng"] == selected_thang]

                st.dataframe(results, hide_index=True)

                # Biểu đồ tiến bộ
                if "Tháng" in df.columns and "Tổng điểm" in df.columns:
                    df_student = df[df["ID"] == str(student_id)]
                    df_student["Tổng điểm"] = pd.to_numeric(df_student["Tổng điểm"], errors="coerce").fillna(0)
                    fig = px.line(
                        df_student,
                        x="Tháng",
                        y="Tổng điểm",
                        title=f"📈 Biểu đồ tiến bộ của {ten_hs}",
                        markers=True
                    )
                    st.plotly_chart(fig)

                if st.button("📋 Tạo nhận xét AI"):
                    nhan_xet = ai_nhan_xet(results)
                    if nhan_xet:
                        st.success("✅ Nhận xét đã tạo:")
                        st.write(nhan_xet)

                        pdf_file = export_pdf(ten_hs, nhan_xet)
                        with open(pdf_file, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode()
                            href = f'<a href="data:application/pdf;base64,{b64}" download="nhan_xet_{ten_hs}.pdf">📄 Tải nhận xét PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Không tìm thấy học sinh với ID này.")

    # ------------------ THỐNG KÊ ------------------
    elif menu == "Thống kê lớp":
        st.subheader("📊 Thống kê lớp")

        cols = ["ID", "Họ tên", "Tổng điểm"]
        df_filtered = df[[c for c in cols if c in df.columns]].copy()
        if "Tổng điểm" in df_filtered.columns:
            df_filtered["Tổng điểm"] = pd.to_numeric(df_filtered["Tổng điểm"], errors="coerce").fillna(0).astype(int)

        df_grouped = (
            df_filtered.groupby(["ID", "Họ tên"], as_index=False)["Tổng điểm"]
            .sum()
            .sort_values(by="Tổng điểm", ascending=False)
        )

        def xep_loai(diem):
            if diem >= 800:
                return "Xuất sắc 🏆"
            elif diem >= 700:
                return "Tốt 👍"
            elif diem >= 600:
                return "Khá 🙂"
            else:
                return "Cần cố gắng ⚠️"

        df_grouped["Xếp loại"] = df_grouped["Tổng điểm"].apply(xep_loai)
        st.dataframe(df_grouped, hide_index=True)

        # Biểu đồ tổng thể
        fig_class = px.bar(
            df_grouped,
            x="Họ tên",
            y="Tổng điểm",
            text="Tổng điểm",
            title="📊 Tổng điểm toàn lớp",
            color="Xếp loại"
        )
        st.plotly_chart(fig_class)

        # Top 4
        st.subheader("🏆 Top 4 học sinh có tổng điểm cao nhất")
        st.dataframe(df_grouped.head(4), hide_index=True)


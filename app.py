import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import plotly.express as px
from fpdf import FPDF
import tempfile
import base64
import os

# ---------------------------
# ⚙️ Cấu hình Streamlit
# ---------------------------
st.set_page_config(page_title="Tình hình học tập và rèn luyện  của học sinh", page_icon="📘", layout="wide")

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

st.title("📘 Tình hình học tập và rèn luyện của học sinh")

# ---------------------------
# 📊 Hàm tải dữ liệu Google Sheets (ĐÃ CHỈNH)
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

        # 🔹 Bỏ dòng trống hoàn toàn
        df = df[df.apply(lambda row: not all(str(x).strip() == "" for x in row), axis=1)]

        # 🔹 Điền lại các ô trống cho ID và Họ tên (để các dòng của 1 học sinh nối tiếp nhau)
        if {"ID", "Họ tên"}.issubset(df.columns):
            df["ID"] = df["ID"].replace("", None)
            df["Họ tên"] = df["Họ tên"].replace("", None)
            df[["ID", "Họ tên"]] = df[["ID", "Họ tên"]].ffill()

        # 🔹 Chuẩn hoá cột Tháng và Tuần để tránh lỗi không hiển thị
        for col in ["Tháng", "Tuần"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace(["", "None", "nan"], None)
                df[col] = df[col].ffill()  # điền các ô trống cùng nhóm
                df[col] = pd.to_numeric(df[col], errors="coerce")  # ép kiểu về số (vd: 1, 2, 3,...)

        # 🔹 Thay thế toàn bộ "None"/"nan" bằng rỗng
        df = df.replace(["None", "nan", None], "")

        return sheet, df
    except Exception as e:
        st.error("❌ Lỗi tải dữ liệu Google Sheets")
        st.exception(e)
        return None, None

# ---------------------------
# 🤖 Hàm AI nhận xét gửi phụ huynh
# ---------------------------
def ai_nhan_xet(thong_tin):
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        prompt = f"""
        Bạn là giáo viên chủ nhiệm. Dưới đây là dữ liệu học tập và rèn luyện của học sinh:

        {thong_tin.to_dict(orient="records")}

        Hãy viết **một đoạn nhận xét gửi đến phụ huynh học sinh** với yêu cầu sau:
        - Mở đầu bằng lời chào: “Kính gửi quý phụ huynh em [Tên học sinh],”
        - Giọng văn nhẹ nhàng, tôn trọng, mang tính giáo dục và động viên.
        - Nêu rõ ưu điểm, tinh thần học tập, thái độ rèn luyện của học sinh.
        - Nếu có hạn chế, hãy diễn đạt khéo léo để phụ huynh hiểu và đồng hành cùng con.
        - Cuối đoạn có thể thêm lời cảm ơn phụ huynh đã quan tâm, phối hợp cùng nhà trường.
        - Không xưng “em” trực tiếp với học sinh, thay bằng “em [Tên]”, “học sinh”, hoặc “cháu”.
        """

        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là giáo viên chủ nhiệm tận tâm, viết thư nhận xét gửi đến phụ huynh học sinh, giọng văn thân thiện, lịch sự và khích lệ."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=700
        )
        return resp.choices[0].message.content
    except Exception as e:
        st.error("❌ Lỗi khi tạo nhận xét AI gửi phụ huynh")
        st.exception(e)
        return None

# ---------------------------
# 🧾 Hàm xuất PDF tiếng Việt
# ---------------------------
def export_pdf(ten_hs, nhan_xet):
    pdf = FPDF()
    pdf.add_page()
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", "", 14)
    pdf.cell(0, 10, "THƯ NHẬN XÉT GỬI PHỤ HUYNH", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("DejaVu", "", 12)
    pdf.multi_cell(0, 8, f"Học sinh: {ten_hs}\n\n{nhan_xet}")

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

                # Hiển thị danh sách tháng hợp lệ
                if "Tháng" in df.columns:
                    thang_list = sorted([int(x) for x in df["Tháng"].dropna().unique() if str(x).isdigit()])
                    selected_thang = st.selectbox("📅 Chọn tháng để xem kết quả", thang_list)
                    results = results[results["Tháng"] == selected_thang]

                st.dataframe(results, hide_index=True)

                if "Tháng" in df.columns and "Tổng điểm" in df.columns:
                    df_student = df[df["ID"] == str(student_id)].copy()
                    df_student["Tổng điểm"] = pd.to_numeric(df_student["Tổng điểm"], errors="coerce").fillna(0)
                    fig = px.line(df_student, x="Tháng", y="Tổng điểm", title=f"📈 Biểu đồ tiến bộ của {ten_hs}", markers=True)
                    st.plotly_chart(fig)

                if st.button("📋 Nhận xét"):
                    nhan_xet = ai_nhan_xet(results)
                    if nhan_xet:
                        st.success("✅ Nhận xét đã tạo (gửi phụ huynh):")
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
        df_filtered["Tổng điểm"] = pd.to_numeric(df_filtered["Tổng điểm"], errors="coerce").fillna(0).astype(int)

        df_grouped = df_filtered.groupby(["ID", "Họ tên"], as_index=False)["Tổng điểm"].sum().sort_values(by="Tổng điểm", ascending=False)

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

        fig_class = px.bar(df_grouped, x="Họ tên", y="Tổng điểm", text="Tổng điểm", title="📊 Tổng điểm toàn lớp", color="Xếp loại")
        st.plotly_chart(fig_class)

        st.subheader("🏆 Top 4 học sinh có tổng điểm cao nhất")
        st.dataframe(df_grouped.head(4), hide_index=True)

        # ------------------ XUẤT PDF TOÀN LỚP ------------------
        st.subheader("📄 Xuất nhận xét AI toàn lớp")

        if st.button("🧠 Tạo và tải tất cả nhận xét PDF"):
            all_comments = []
            for _, row in df_grouped.iterrows():
                ten_hs = row["Họ tên"]
                hs_data = df[df["Họ tên"] == ten_hs]
                nhan_xet = ai_nhan_xet(hs_data)
                all_comments.append(f"Họ tên: {ten_hs}\n{nhan_xet}\n\n" + "-"*80 + "\n")

            pdf = FPDF()
            pdf.add_page()
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            pdf.add_font("DejaVu", "", font_path, uni=True)
            pdf.set_font("DejaVu", "", 14)
            pdf.cell(0, 10, "BÁO CÁO NHẬN XÉT GỬI PHỤ HUYNH TOÀN LỚP", ln=True, align="C")
            pdf.ln(10)
            pdf.set_font("DejaVu", "", 11)
            for comment in all_comments:
                pdf.multi_cell(0, 8, comment)
                pdf.ln(4)

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            pdf.output(temp_file.name)
            with open(temp_file.name, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="nhan_xet_toan_lop.pdf">📘 Tải báo cáo toàn lớp (PDF)</a>'
                st.markdown(href, unsafe_allow_html=True)




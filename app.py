import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import plotly.express as px

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
    div[data-baseweb="input"] > input {
        border: 1px solid #dadce0;
        border-radius: 8px;
        padding: 6px 12px;
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

        # ❌ KHÔNG xoá hàng trống (chỉ loại bỏ hàng thực sự trống hoàn toàn)
        df = df[df.apply(lambda row: not all(str(x).strip() == "" for x in row), axis=1)]

        # ✅ Giữ nguyên các dòng có ID và Tuần
        if {"ID", "Tuần"}.issubset(df.columns):
            df = df[(df["ID"].notna()) & (df["ID"] != "")]

        # ✅ Điền lại ID & Họ tên để hiển thị liên tục
        if {"ID", "Họ tên"}.issubset(df.columns):
            df[["ID", "Họ tên"]] = df[["ID", "Họ tên"]].ffill()

        # 🧹 Chuyển các giá trị "None", "nan" thành chuỗi rỗng để hiển thị trống
        df = df.replace(["None", "nan", None, ""], "")

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

        Hãy viết một nhận xét gửi phụ huynh:
        - Phân tích kết quả học tập, nêu điểm mạnh – điểm yếu.
        - Nhận xét thái độ, kỷ luật, phong trào.
        - Cuối cùng khuyên nhẹ nhàng, tích cực.
        """

        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là giáo viên chủ nhiệm tận tâm, viết nhận xét thân thiện, tự nhiên, truyền cảm hứng."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return resp.choices[0].message.content

    except Exception as e:
        st.error("❌ Lỗi khi gọi OpenAI API")
        st.exception(e)
        return None

# ---------------------------
# 🧭 Giao diện chính
# ---------------------------
sheet, df = load_data()

if df is not None:
    if "ID" in df.columns:
        df["ID"] = df["ID"].astype(str)

    menu = st.sidebar.radio("📌 Chọn chức năng", ["Tra cứu học sinh", "Thống kê lớp"])

    # ------------------ TRA CỨU ------------------
    if menu == "Tra cứu học sinh":
        st.subheader("🔍 Tra cứu học sinh")
        student_id = st.text_input("Nhập ID")

        if student_id:
            results = df[df["ID"] == str(student_id)]

            if not results.empty:
                ten_hs = results["Họ tên"].iloc[0]
                st.subheader(f"📌 Kết quả học tập của {ten_hs} (ID: {student_id})")

                # Hiển thị đầy đủ các dòng T2–T7, ô trống không hiện None
                st.dataframe(results.fillna(""))

                if st.button("📌 Nhận xét"):
                    nhan_xet = ai_nhan_xet(results)
                    if nhan_xet:
                        st.success("✅ Nhận xét đã tạo:")
                        st.write(nhan_xet)
            else:
                st.info("⚠️ Không tìm thấy học sinh")

    # ------------------ THỐNG KÊ ------------------
    elif menu == "Thống kê lớp":
        st.subheader("📊 Thống kê lớp")

        if "Tổng điểm rèn luyện" in df.columns:
            st.metric("Điểm rèn luyện trung bình cả lớp", round(df["Tổng điểm rèn luyện"].astype(float).mean(), 2))

        cols_check = ["Đi học đúng giờ", "Đồng phục", "Thái độ học tập", "Trật tự", "Vệ sinh", "Phong trào"]
        vi_pham = {}
        for col in cols_check:
            if col in df.columns:
                vi_pham[col] = (df[col] == "X").sum()

        if vi_pham:
            fig = px.bar(
                x=list(vi_pham.keys()),
                y=list(vi_pham.values()),
                labels={"x": "Tiêu chí", "y": "Số lần vi phạm"},
                title="📌 Số lần vi phạm theo tiêu chí"
            )
            st.plotly_chart(fig)

        # ✅ Top học sinh có điểm rèn luyện cao nhất
        if {"ID", "Họ tên", "Tổng điểm rèn luyện"}.issubset(df.columns):
            top4 = (
                df.groupby(["ID", "Họ tên"], as_index=False)["Tổng điểm rèn luyện"]
                .sum()
                .sort_values(by="Tổng điểm rèn luyện", ascending=False)
                .head(4)
            )
            top4["Tổng điểm rèn luyện"] = top4["Tổng điểm rèn luyện"].astype(int)
            st.subheader("🏆 Top 4 học sinh có điểm rèn luyện cao nhất (Tuyên dương)")
            st.dataframe(top4[["ID", "Họ tên", "Tổng điểm rèn luyện"]])





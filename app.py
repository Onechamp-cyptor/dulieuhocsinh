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

        # 🧹 Xoá hàng trống thật sự
        df = df[df.apply(lambda row: not all(str(x).strip() == "" for x in row), axis=1)]

        # ✅ Tự động điền ID và Họ tên bị trống (để hiện đủ T2–T7)
        if {"ID", "Họ tên"}.issubset(df.columns):
            df["ID"] = df["ID"].replace("", None)
            df["Họ tên"] = df["Họ tên"].replace("", None)
            df[["ID", "Họ tên"]] = df[["ID", "Họ tên"]].ffill()

        # ✅ Xử lý None/nan => trống
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
        Bạn là giáo viên chủ nhiệm. Đây là dữ liệu chi tiết của học sinh (có điểm từng môn):

        {thong_tin.to_dict(orient="records")}

        Quy tắc phân tích:
        - Trên 8 điểm: học tập tốt
        - Từ 6 đến 8 điểm: có sự nỗ lực trong học tập
        - Dưới 5 điểm: cần cố gắng thêm

        Nhiệm vụ:
        Hãy viết một nhận xét gửi phụ huynh theo phong cách mềm mại, tự nhiên, tránh liệt kê khô khan. 
        - Mở đầu: chào phụ huynh và giới thiệu mục đích.
        - Phân tích chung tình hình học tập, nêu môn nào em làm tốt, môn nào có sự nỗ lực, môn nào cần cố gắng thêm.
        - Nêu ưu điểm, hạn chế, thái độ, kỷ luật, vệ sinh, phong trào.
        - Kết thúc bằng lời khuyên thân thiện, tích cực dành cho phụ huynh.
        """

        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là giáo viên chủ nhiệm tận tâm, viết nhận xét thân thiện, tự nhiên, truyền cảm hứng."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
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

                st.dataframe(results)

                if st.button("📋 Nhận xét"):
                    nhan_xet = ai_nhan_xet(results)
                    if nhan_xet:
                        st.success("✅ Nhận xét đã tạo:")
                        st.write(nhan_xet)
            else:
                st.info("⚠️ Không tìm thấy học sinh")

    # ------------------ THỐNG KÊ ------------------
    elif menu == "Thống kê lớp":
        st.subheader("📊 Thống kê lớp")

        # ✅ Trung bình rèn luyện
        if "Tổng điểm rèn luyện" in df.columns:
            st.metric("Điểm rèn luyện trung bình cả lớp", round(df["Tổng điểm rèn luyện"].astype(float).mean(), 2))

        # ✅ Thống kê toàn bộ học sinh
        if {"ID", "Họ tên", "Tổng điểm rèn luyện"}.issubset(df.columns):
            tong_hs = (
                df.groupby(["ID", "Họ tên"], as_index=False)["Tổng điểm rèn luyện"]
                .sum()
                .sort_values(by="Tổng điểm rèn luyện", ascending=False)
            )

            tong_hs["Tổng điểm rèn luyện"] = tong_hs["Tổng điểm rèn luyện"].astype(float)
            tong_hs["Xếp loại"] = tong_hs["Tổng điểm rèn luyện"].apply(
                lambda x: "Tốt" if x >= 500 else ("Khá" if x >= 400 else "Trung bình")
            )

            st.subheader("📋 Thống kê toàn bộ học sinh")
            st.dataframe(tong_hs)

            # Biểu đồ top học sinh
            fig_top = px.bar(
                tong_hs.head(10),
                x="Họ tên",
                y="Tổng điểm rèn luyện",
                color="Xếp loại",
                text="Tổng điểm rèn luyện",
                title="🏆 Top học sinh có điểm rèn luyện cao nhất"
            )
            st.plotly_chart(fig_top)

        # ✅ Biểu đồ thống kê vi phạm
        cols_check = ["Đi học đúng giờ", "Đồng phục", "Thái độ học tập", "Trật tự", "Vệ sinh", "Phong trào"]
        vi_pham = {}
        for col in cols_check:
            if col in df.columns:
                vi_pham[col] = (df[col] == "X").sum()

        if vi_pham:
            st.subheader("📉 Thống kê vi phạm theo tiêu chí")
            fig_vp = px.bar(
                x=list(vi_pham.keys()),
                y=list(vi_pham.values()),
                labels={"x": "Tiêu chí", "y": "Số lần vi phạm"},
                title="📌 Số lần vi phạm trong toàn lớp"
            )
            st.plotly_chart(fig_vp)

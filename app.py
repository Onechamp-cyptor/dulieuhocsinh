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

# ---------------------------
# CSS style Google-like
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

        data = sheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])

        df = df.replace("", None)

        if {"ID", "Họ tên"}.issubset(df.columns):
            df[["ID", "Họ tên"]] = df[["ID", "Họ tên"]].ffill()

        return sheet, df
    except Exception as e:
        st.error("❌ Lỗi tải dữ liệu Google Sheets")
        st.exception(e)
        return None, None

# ---------------------------
# Quy đổi dữ liệu tick / X
# ---------------------------
def xu_ly_du_lieu(thong_tin):
    df = thong_tin.copy()
    for col in df.columns:
        df[col] = df[col].replace({
            "✓": "Đạt (+20 điểm)",
            "X": "Chưa đạt (-30 điểm)",
            None: "Không ghi nhận",
            "": "Không ghi nhận",
            True: "Có (✓)",
            False: "Không"
        })
    return df

# ---------------------------
# Hàm AI nhận xét học sinh (AI tự phân tích mềm mại)
# ---------------------------
def ai_nhan_xet(thong_tin):
    try:
        openai.api_key = st.secrets["openai"]["api_key"]

        data_quydoi = xu_ly_du_lieu(thong_tin)

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
        - Phân tích chung tình hình học tập, nêu môn nào em làm tốt, môn nào có sự nỗ lực, môn nào cần cố gắng thêm (AI tự diễn đạt dựa vào điểm).
        - Nêu ưu điểm và hạn chế chung.
        - Nhận xét thêm về thái độ, kỷ luật, vệ sinh, phong trào.
        - Kết thúc bằng lời khuyên thân thiện, tích cực dành cho phụ huynh.
        """

        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là giáo viên chủ nhiệm tận tâm, viết nhận xét rõ ràng, thân thiện, mượt mà và truyền cảm hứng."},
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
# Giao diện chính
# ---------------------------
sheet, df = load_data()

if df is not None:
    if "ID" in df.columns:
        df["ID"] = df["ID"].astype(str)

    if "Tổng điểm" in df.columns:
        df["Tổng điểm"] = pd.to_numeric(df["Tổng điểm"], errors="coerce").fillna(0)
    if "Tổng điểm tuần" in df.columns:
        df["Tổng điểm tuần"] = pd.to_numeric(df["Tổng điểm tuần"], errors="coerce").fillna(0)

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

                if {"Tuần", "Tổng điểm tuần"}.issubset(results.columns):
                    tong_tuan = results.groupby("Tuần", as_index=False)["Tổng điểm tuần"].sum()
                    st.subheader("📊 Tổng điểm theo từng tuần")
                    st.dataframe(tong_tuan)

                if st.button("📌 Nhận xét phụ huynh"):
                    nhan_xet = ai_nhan_xet(results)
                    if nhan_xet:
                        st.success("✅ Nhận xét đã tạo:")
                        st.write(nhan_xet)
            else:
                st.info("⚠️ Không tìm thấy học sinh")

    # ------------------ THỐNG KÊ ------------------
    elif menu == "Thống kê lớp":
        st.subheader("📊 Thống kê lớp")

        if "Tổng điểm tuần" in df.columns:
            st.metric("Điểm trung bình cả lớp", round(df["Tổng điểm tuần"].mean(), 2))

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

        if {"ID", "Họ tên", "Tổng điểm tuần"}.issubset(df.columns):
            top4 = (
                df.groupby(["ID", "Họ tên"], as_index=False)["Tổng điểm tuần"]
                .sum()
                .sort_values(by="Tổng điểm tuần", ascending=False)
                .head(4)
            )
            top4["Tổng điểm tuần"] = top4["Tổng điểm tuần"].astype(int)

            st.subheader("🏆 Top 4 học sinh điểm cao nhất (Tuyên dương)")
            st.dataframe(top4[["ID", "Họ tên", "Tổng điểm tuần"]])



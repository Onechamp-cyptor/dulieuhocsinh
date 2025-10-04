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

        # ✅ Tự động điền ID & Họ tên bị trống
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

        Viết nhận xét gửi phụ huynh theo phong cách nhẹ nhàng, tự nhiên.
        """

        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là giáo viên chủ nhiệm tận tâm, viết nhận xét thân thiện và truyền cảm hứng."},
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
                st.info(f"✅ ID hợp lệ: {student_id} → Học sinh: **{ten_hs}**")

                st.subheader(f"📋 Kết quả học tập của {ten_hs} (ID: {student_id})")
                st.dataframe(results)

                if st.button("📋 Nhận xét"):
                    nhan_xet = ai_nhan_xet(results)
                    if nhan_xet:
                        st.success("✅ Nhận xét đã tạo:")
                        st.write(nhan_xet)
            else:
                st.warning("⚠️ Không tìm thấy học sinh với ID này")

    # ------------------ THỐNG KÊ ------------------
    elif menu == "Thống kê lớp":
        st.subheader("📊 Thống kê lớp")

        # ✅ Chỉ lấy các cột cần thiết
        cols = [
            "ID", "Họ tên", "Điểm danh", "Đi học đúng giờ", "Đồng phục",
            "Thái độ học tập", "Trật tự", "Vệ sinh", "Phong trào", "Tổng điểm"
        ]
        df_filtered = df[[c for c in cols if c in df.columns]].copy()

        # ✅ Chuyển Tổng điểm sang số
        if "Tổng điểm" in df_filtered.columns:
            df_filtered["Tổng điểm"] = pd.to_numeric(df_filtered["Tổng điểm"], errors="coerce").fillna(0).astype(int)

        # ✅ Tự động xếp loại
        def xep_loai(diem):
            if diem >= 800:
                return "Xuất sắc 🏆"
            elif diem >= 700:
                return "Tốt 👍"
            elif diem >= 600:
                return "Khá 🙂"
            else:
                return "Cần cố gắng ⚠️"

        df_filtered["Xếp loại"] = df_filtered["Tổng điểm"].apply(xep_loai)

        # ✅ Hiển thị gọn 4 cột: ID, Họ tên, Tổng điểm, Xếp loại
        cols_show = ["ID", "Họ tên", "Tổng điểm", "Xếp loại"]
        df_show = df_filtered[[c for c in cols_show if c in df_filtered.columns]]
        st.dataframe(df_show)

        # ✅ Thống kê vi phạm
        st.subheader("📈 Thống kê vi phạm theo tiêu chí")
        cols_check = ["Điểm danh", "Đi học đúng giờ", "Đồng phục", "Thái độ học tập", "Trật tự", "Vệ sinh", "Phong trào"]
        vi_pham = {col: (df[col] == "X").sum() for col in cols_check if col in df.columns}

        if vi_pham:
            fig_vp = px.bar(
                x=list(vi_pham.keys()),
                y=list(vi_pham.values()),
                labels={"x": "Tiêu chí", "y": "Số lần vi phạm"},
                title="📌 Số lần vi phạm toàn lớp"
            )
            st.plotly_chart(fig_vp)

        # ✅ Top 4 học sinh có Tổng điểm cao nhất
        if {"ID", "Họ tên", "Tổng điểm"}.issubset(df_filtered.columns):
            top4 = (
                df_filtered.groupby(["ID", "Họ tên"], as_index=False)["Tổng điểm"]
                .sum()
                .sort_values(by="Tổng điểm", ascending=False)
                .head(4)
            )
            top4["Xếp loại"] = top4["Tổng điểm"].apply(xep_loai)

            st.subheader("🏆 Top 4 học sinh có tổng điểm cao nhất")
            st.dataframe(top4)

            fig_top = px.bar(
                top4,
                x="Họ tên",
                y="Tổng điểm",
                text="Tổng điểm",
                title="📊 Biểu đồ Top 4 học sinh có tổng điểm cao nhất",
                color="Họ tên"
            )
            st.plotly_chart(fig_top)



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

        # Lấy toàn bộ dữ liệu kể cả dòng trống
        data = sheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])

        # Điền ID và Họ tên xuống các dòng trống (fix chỉ hiện 1 dòng T2)
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
            "": "Không ghi nhận",
            True: "Có (✓)",
            False: "Không"
        })
    return df

# ---------------------------
# Hàm AI nhận xét học sinh
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
    # Chuyển ID sang string
    if "ID" in df.columns:
        df["ID"] = df["ID"].astype(str)

    # Chuyển điểm về số
    if "Tổng điểm" in df.columns:
        df["Tổng điểm"] = pd.to_numeric(df["Tổng điểm"], errors="coerce").fillna(0)
    if "Tổng điểm tuần" in df.columns:
        df["Tổng điểm tuần"] = pd.to_numeric(df["Tổng điểm tuần"], errors="coerce").fillna(0)

    # Sidebar chọn chức năng
    menu = st.sidebar.radio("📌 Chọn chức năng", ["Tra cứu học sinh", "Thống kê lớp"])

    # ------------------ TRA CỨU ------------------
    if menu == "Tra cứu học sinh":
        st.subheader("🔍 Tra cứu học sinh")
        student_id = st.text_input("Nhập ID")
        student_name = st.text_input("Hoặc nhập tên")

        # Lấy danh sách tuần hợp lệ
        if "Tuần" in df.columns:
            week_list = sorted([str(w) for w in df["Tuần"].dropna().unique()])
            selected_week = st.selectbox("📅 Chọn tuần", week_list)
        else:
            st.error("❌ Thiếu cột 'Tuần' trong Google Sheet")
            selected_week = None

        results = None
        if selected_week:
            if student_id:
                results = df[(df["ID"] == str(student_id)) & (df["Tuần"].astype(str) == str(selected_week))]
            elif student_name:
                results = df[(df["Họ tên"].str.contains(student_name, case=False)) & (df["Tuần"].astype(str) == str(selected_week))]

        if results is not None and not results.empty:
            # Sắp xếp theo Thứ
            if "Thứ" in results.columns:
                thu_order = ["T2", "T3", "T4", "T5", "T6", "T7"]
                results["Thứ"] = pd.Categorical(results["Thứ"], categories=thu_order, ordered=True)
                results = results.sort_values("Thứ")

            # --------- HIỂN THỊ CHI TIẾT 6 DÒNG ----------
            st.subheader(f"📌 Chi tiết tuần {selected_week} (T2 → T7)")
            st.dataframe(results)

            # --------- HIỂN THỊ TỔNG HỢP TUẦN ----------
            if "Tổng điểm" in results.columns:
                tong_tuan = results.groupby(["ID", "Họ tên"], as_index=False)["Tổng điểm"].sum()
                tong_tuan.rename(columns={"Tổng điểm": "Tổng điểm tuần"}, inplace=True)

                st.subheader("📊 Tổng điểm tuần (T2 → T7)")
                st.dataframe(tong_tuan)

            # --------- NHẬN XÉT AI ----------
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

        # Số lần vi phạm
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

        # Top 4 học sinh
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


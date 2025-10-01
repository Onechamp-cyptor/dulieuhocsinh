import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import openai
import pandas as pd

# --- K?t n?i Google Service Account ---
creds_dict = dict(st.secrets["google_service_account"])
creds = Credentials.from_service_account_info(creds_dict)
client_gs = gspread.authorize(creds)

# --- L?y OpenAI API key ---
openai.api_key = st.secrets["openai"]["api_key"]

# --- L?y Sheet ID t? secrets ---
SHEET_ID = st.secrets["sheets"]["sheet_id"]

# --- K?t n?i Google Sheet ---
sheet = client_gs.open_by_key(SHEET_ID).sheet1
data = sheet.get_all_records()
df = pd.DataFrame(data)

# --- Giao di?n ---
st.title("?? Qu?n lý di?m h?c sinh b?ng AI")

st.subheader("?? B?ng di?m hi?n t?i")
st.dataframe(df, use_container_width=True)

# --- Tra c?u h?c sinh ---
st.subheader("?? Tra c?u di?m h?c sinh")
student_name = st.text_input("Nh?p tên h?c sinh:")

if student_name:
    if "H? tên" in df.columns:
        results = df[df["H? tên"].str.contains(student_name, case=False)]
        if not results.empty:
            st.success("? K?t qu? tìm th?y:")
            st.dataframe(results, use_container_width=True)
        else:
            st.warning("?? Không tìm th?y h?c sinh này.")
    else:
        st.error("? Không tìm th?y c?t 'H? tên' trong Google Sheet!")

# --- Tích h?p AI ---
st.subheader("?? H?i AI v? k?t qu? h?c t?p")
question = st.text_area("Nh?p câu h?i (ví d?: Nh?n xét v? Nguy?n Van A):")

if st.button("H?i AI"):
    if not question:
        st.warning("?? B?n c?n nh?p câu h?i.")
    else:
        context = df.to_string(index=False)
        prompt = f"""
        Ðây là b?ng di?m c?a h?c sinh:
        {context}

        Câu h?i: {question}

        Hãy tr? l?i rõ ràng, d? hi?u cho ph? huynh.
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "B?n là m?t c? v?n h?c t?p."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            answer = response.choices[0].message.content
            st.success("?? Tr? l?i c?a AI:")
            st.write(answer)
        except Exception as e:
            st.error(f"? L?i khi g?i AI: {e}")

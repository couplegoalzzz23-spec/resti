# ==========================================================
# IMPORT LIBRARY
# ==========================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================================
# CONFIGURATION
# ==========================================================
st.set_page_config(
    page_title="ACS Tactical Weather Dashboard",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# DATA LOADER
# ==========================================================
@st.cache_data
def load_data():
    """
    Membaca seluruh file excel yang ada di direktori.
    Memastikan openpyxl terinstall untuk membaca .xlsx
    """
    file_names = [
        "rekap_temperature_2021_2025.xlsx",
        "rekap_rh_max_min_2021_2025.xlsx",
        "rekap_visibility_2021_2025.xlsx",
        "rekap_wind_2021_2025.xlsx"
    ]
    
    dfs = []
    found_files = False
    
    for file in file_names:
        if os.path.exists(file):
            try:
                # Membaca excel dengan engine openpyxl
                df_temp = pd.read_excel(file, engine='openpyxl')
                dfs.append(df_temp)
                found_files = True
            except Exception as e:
                st.error(f"Gagal membaca {file}: {e}")
    
    if not found_files:
        st.error("Data tidak ditemukan! Pastikan file .xlsx berada di folder yang sama dengan app.py.")
        st.stop()
        
    # Menggabungkan data (outer join agar data tidak hilang)
    from functools import reduce
    df_final = reduce(lambda left, right: pd.merge(left, right, on='Datetime', how='outer'), dfs)
    
    # Konversi Datetime
    df_final['Datetime'] = pd.to_datetime(df_final['Datetime'])
    return df_final

# ==========================================================
# PREPROCESSING
# ==========================================================
def preprocess_data(df):
    df["Hour"] = df["Datetime"].dt.hour
    df["Year"] = df["Datetime"].dt.year
    return df

# ==========================================================
# MAIN PAGE
# ==========================================================
def main():
    st.title("🎛️ Dashboard Analisis Cuaca Bandara")
    
    # 1. Load & Process
    df = load_data()
    df = preprocess_data(df)
    
    # Sidebar
    menu = ["Home", "Overview"]
    choice = st.sidebar.selectbox("Navigasi", menu)
    
    if choice == "Home":
        st.subheader("Data Overview")
        st.dataframe(df.head(20))
        st.success("Data berhasil dimuat dan diproses dari file Excel!")
        
    elif choice == "Overview":
        st.subheader("Ringkasan Data")
        st.write(f"Total baris data: {len(df)}")
        st.line_chart(df.set_index("Datetime")["Temperature"])

if __name__ == "__main__":
    main()

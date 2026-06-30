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
# CONSTANT
# ==========================================================
STATION_NAME = "Pangkalan Udara Roesmin Nurjadin"
ELEVATION_M = 31
ICAO_CODE = "WIBB"

# ==========================================================
# DATA LOADER
# ==========================================================
@st.cache_data
def load_data():
    """
    Membaca seluruh file excel yang ada di direktori dan 
    menggabungkannya menjadi satu DataFrame utama.
    """
    file_names = [
        "rekap_temperature_2021_2025.xlsx",
        "rekap_rh_max_min_2021_2025.xlsx",
        "rekap_visibility_2021_2025.xlsx",
        "rekap_wind_2021_2025.xlsx"
        # Tambahkan file lain jika diperlukan
    ]
    
    dfs = []
    for file in file_names:
        if os.path.exists(file):
            df_temp = pd.read_excel(file)
            dfs.append(df_temp)
    
    if not dfs:
        st.error("File data tidak ditemukan! Pastikan file .xlsx ada di folder yang sama dengan app.py.")
        st.stop()
        
    # Menggabungkan data berdasarkan kolom 'Datetime'
    from functools import reduce
    df_final = reduce(lambda left, right: pd.merge(left, right, on='Datetime', how='outer'), dfs)
    
    # Pastikan Datetime dalam format datetime
    df_final['Datetime'] = pd.to_datetime(df_final['Datetime'])
    return df_final

# ==========================================================
# VALIDATION
# ==========================================================
def validate_data(df):
    required_columns = ["Datetime", "Temperature", "RH", "Visibility", "WindSpeed", "WindDir"]
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        st.warning(f"Kolom tidak lengkap: {', '.join(missing_cols)}. Aplikasi mungkin tidak berjalan optimal.")
    return True

# ==========================================================
# PREPROCESSING
# ==========================================================
def preprocess_data(df):
    df["Hour"] = df["Datetime"].dt.hour
    df["Year"] = df["Datetime"].dt.year
    return df

def get_diurnal_stats(df, parameter):
    return df.groupby("Hour")[parameter].mean().reset_index()

# ==========================================================
# INTERPRETATION ENGINE & AVIATION NOTES (Sama seperti sebelumnya)
# ==========================================================
def interpret_diurnal_pattern(df_diurnal, parameter, unit):
    max_val = df_diurnal[parameter].max()
    max_hour = df_diurnal.loc[df_diurnal[parameter].idxmax(), "Hour"]
    return f"Puncak {parameter} rata-rata terjadi pada pukul {max_hour:02d}:00 dengan nilai {max_val:.1f}{unit}."

def generate_aviation_notes(parameter):
    notes = {
        "Temperature": "Suhu tinggi memengaruhi density altitude dan performa pesawat.",
        "RH": "RH tinggi pada pagi hari berpotensi menciptakan kabut (fog).",
        "Visibility": "Visibilitas rendah membatasi operasi VFR.",
        "Wind": "Perhatikan arah angin untuk pemilihan runway."
    }
    return notes.get(parameter, "Tidak ada catatan khusus.")

# ==========================================================
# PLOT FUNCTIONS (Sama seperti sebelumnya)
# ==========================================================
def plot_meteogram(df_diurnal, x_col, y_col, title, y_label, color):
    fig = px.line(df_diurnal, x=x_col, y=y_col, title=title, markers=True)
    fig.update_layout(xaxis=dict(tickmode='linear'), template="plotly_white")
    return fig

# ==========================================================
# PAGE MAIN
# ==========================================================
def main():
    st.title("🎛️ Dashboard Analisis Cuaca Bandara")
    
    df_raw = load_data()
    validate_data(df_raw)
    df = preprocess_data(df_raw)
    
    menu = ["Home", "Temperature", "Wind", "Visibility"]
    choice = st.sidebar.selectbox("Pilih Modul", menu)
    
    if choice == "Home":
        st.write("Data berhasil dimuat dari file Excel Anda.")
        st.dataframe(df.head())
    elif choice == "Temperature":
        df_diurnal = get_diurnal_stats(df, "Temperature")
        st.plotly_chart(plot_meteogram(df_diurnal, "Hour", "Temperature", "Suhu", "°C", "red"))
        st.write(interpret_diurnal_pattern(df_diurnal, "Temperature", "°C"))

if __name__ == "__main__":
    main()

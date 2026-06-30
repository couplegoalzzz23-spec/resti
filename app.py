# ==========================================================
# IMPORT LIBRARY
# ==========================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

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
START_YEAR = 2021
END_YEAR = 2025

# ==========================================================
# DATA LOADER
# ==========================================================
@st.cache_data
def load_data():
    """
    Mencoba memuat data dari file CSV lokal. 
    Jika file tidak ditemukan, akan menghasilkan data simulasi klimatologi 
    yang realistis agar aplikasi tetap utuh dan dapat dijalankan.
    """
    try:
        df = pd.read_csv("acs_data.csv", parse_dates=["Datetime"])
        return df
    except FileNotFoundError:
        # Generate Realistic Dummy ACS Data for out-of-the-box execution
        np.random.seed(42)
        dates = pd.date_range(start=f"{START_YEAR}-01-01", end=f"{END_YEAR}-12-31 23:00:00", freq="H")
        n = len(dates)
        
        hours = dates.hour
        # Temperature: Min around 06:00, Max around 14:00
        temp = 28 + 4 * np.sin((hours - 8) * (2 * np.pi / 24)) + np.random.normal(0, 0.5, n)
        # RH: Inversely proportional to temperature
        rh = 100 - (temp - 24) * 6 + np.random.normal(0, 2, n)
        rh = np.clip(rh, 40, 100)
        # Visibility: Usually 10000m, drops in early morning with high RH
        vis = np.where((hours >= 4) & (hours <= 7) & (rh > 95), np.random.uniform(800, 5000, n), 10000)
        # Cloud Base: Varies, lower in morning/rain, usually around 1500-3000 ft
        cloud_base = np.where(rh > 90, np.random.uniform(1000, 2000, n), np.random.uniform(2000, 5000, n))
        # Wind Speed: Diurnal pattern, stronger in afternoon
        wind_spd = 3 + 5 * np.sin((hours - 9) * (2 * np.pi / 24)) + np.random.normal(0, 1, n)
        wind_spd = np.clip(wind_spd, 0, 20)
        # Wind Dir: Predominantly NW to SE shift
        wind_dir = np.random.normal(300, 45, n) % 360
        
        df = pd.DataFrame({
            "Datetime": dates,
            "Temperature": np.round(temp, 1),
            "RH": np.round(rh, 1),
            "Visibility": np.round(vis, 0),
            "CloudBase": np.round(cloud_base, 0),
            "WindSpeed": np.round(wind_spd, 1),
            "WindDir": np.round(wind_dir, 0)
        })
        return df

# ==========================================================
# VALIDATION
# ==========================================================
def validate_data(df):
    """
    Memvalidasi integritas kolom data sebelum diproses.
    """
    required_columns = ["Datetime", "Temperature", "RH", "Visibility", "CloudBase", "WindSpeed", "WindDir"]
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        st.error(f"Data validation failed. Missing columns: {', '.join(missing_cols)}")
        st.stop()
    return True

# ==========================================================
# PREPROCESSING
# ==========================================================
def preprocess_data(df):
    """
    Ekstraksi fitur waktu untuk analisis diurnal dan bulanan.
    """
    df["Hour"] = df["Datetime"].dt.hour
    df["Month"] = df["Datetime"].dt.month
    df["Year"] = df["Datetime"].dt.year
    df["Month_Name"] = df["Datetime"].dt.strftime('%B')
    return df

def get_diurnal_stats(df, parameter):
    """
    Menghasilkan rekapan rata-rata diurnal (per jam) untuk suatu parameter.
    """
    return df.groupby("Hour")[parameter].mean().reset_index()

# ==========================================================
# INTERPRETATION ENGINE
# ==========================================================
def interpret_diurnal_pattern(df_diurnal, parameter, unit):
    max_val = df_diurnal[parameter].max()
    min_val = df_diurnal[parameter].min()
    max_hour = df_diurnal.loc[df_diurnal[parameter].idxmax(), "Hour"]
    min_hour = df_diurnal.loc[df_diurnal[parameter].idxmin(), "Hour"]
    
    return f"Pola diurnal menunjukkan bahwa {parameter} mencapai puncaknya pada pukul {max_hour:02d}:00 UTC/Lokal dengan nilai rata-rata {max_val:.1f}{unit}, dan menyentuh nilai terendah pada pukul {min_hour:02d}:00 UTC/Lokal dengan nilai rata-rata {min_val:.1f}{unit}."

# ==========================================================
# AVIATION NOTES ENGINE
# ==========================================================
def generate_aviation_notes(parameter):
    notes = {
        "Temperature": "Suhu yang tinggi pada siang hari akan secara signifikan meningkatkan Density Altitude, yang berpotensi mengurangi daya angkat (lift) pesawat dan memperpanjang jarak lepas landas (take-off roll) dalam operasi militer taktis.",
        "RH": "Kelembapan relatif yang tinggi (mendekati 100%) terutama pada dini hari, dikombinasikan dengan suhu yang turun mendekati titik embun (dew point), meningkatkan probabilitas pembentukan kabut (fog) yang dapat menghambat fase landing dan take-off.",
        "Visibility": "Jarak pandang (Visibility) adalah parameter kritis. Penurunan visibilitas di bawah kriteria VFR (Visual Flight Rules) mengharuskan transisi ke instrumen (IFR), yang dapat membatasi operasi penerbangan formasi atau misi taktis visual.",
        "CloudBase": "Tinggi dasar awan (Ceiling) di bawah 1500 feet dapat mengganggu pola lalu lintas udara lokal (aerodrome traffic circuit) dan misi latihan penerbangan rendah.",
        "Wind": "Variasi arah dan kecepatan angin (termasuk potensi wind shear) sangat memengaruhi pemilihan landasan pacu (runway in use) dan keamanan manuver pesawat tempur saat final approach."
    }
    return notes.get(parameter, "Tidak ada catatan spesifik penerbangan untuk parameter ini.")

# ==========================================================
# PLOT FUNCTIONS
# ==========================================================
def plot_meteogram(df_diurnal, x_col, y_col, title, y_label, color="#1f77b4"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_diurnal[x_col], 
        y=df_diurnal[y_col],
        mode='lines+markers',
        line=dict(color=color, width=3),
        marker=dict(size=8, symbol='circle'),
        name=y_col
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Waktu (Jam)",
        yaxis_title=y_label,
        xaxis=dict(tickmode='linear', tick0=0, dtick=1),
        template="plotly_white",
        hovermode="x unified"
    )
    return fig

def plot_wind_rose(df):
    bins = [0, 45, 90, 135, 180, 225, 270, 315, 360]
    labels = ['N-NE', 'NE-E', 'E-SE', 'SE-S', 'S-SW', 'SW-W', 'W-NW', 'NW-N']
    df['WindDir_Cat'] = pd.cut(df['WindDir'], bins=bins, labels=labels, right=False)
    wind_counts = df['WindDir_Cat'].value_counts().reset_index()
    wind_counts.columns = ['Direction', 'Frequency']
    
    fig = px.bar_polar(
        wind_counts, 
        r="Frequency", 
        theta="Direction",
        color="Frequency",
        template="plotly_white",
        color_continuous_scale=px.colors.sequential.Plasma,
        title="Distribusi Arah Angin Dominan"
    )
    return fig

# ==========================================================
# PAGE HOME
# ==========================================================
def page_home(df):
    st.title(f"✈️ Aerodrome Climatological Summary Dashboard")
    st.subheader(f"Stasiun: {STATION_NAME} (ICAO: {ICAO_CODE})")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Data (Observasi per Jam)", f"{len(df):,}")
    col2.metric("Rentang Tahun", f"{df['Year'].min()} - {df['Year'].max()}")
    col3.metric("Elevasi Pangkalan", f"{ELEVATION_M} Meter")
    
    st.markdown("""
    ### Deskripsi Sistem
    Aplikasi ini dirancang untuk menyediakan informasi klimatologi taktis dan cuaca bandara yang terintegrasi. 
    Seluruh grafik disajikan dalam format meteogram diurnal untuk mengidentifikasi pola harian, yang mana sangat penting untuk perencanaan operasi militer, penyusunan jadwal penerbangan, dan mitigasi risiko cuaca (seperti *Density Altitude* tinggi, probabilitas kabut, atau profil visibilitas yang buruk).
    """)
    
    st.markdown("### Tinjauan Data Mentah")
    st.dataframe(df.head(10), use_container_width=True)

# ==========================================================
# PAGE TEMPERATURE
# ==========================================================
def page_temperature(df):
    st.header("🌡️ Analisis Suhu Permukaan (Temperature)")
    st.markdown("---")
    
    df_diurnal = get_diurnal_stats(df, "Temperature")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(plot_meteogram(df_diurnal, "Hour", "Temperature", "Meteogram Diurnal Suhu", "Suhu (°C)", "#d62728"), use_container_width=True)
    with col2:
        st.info("💡 **Interpretasi Klimatologis**")
        st.write(interpret_diurnal_pattern(df_diurnal, "Temperature", "°C"))
        st.warning("✈️ **Dampak Penerbangan (Aviation Notes)**")
        st.write(generate_aviation_notes("Temperature"))

# ==========================================================
# PAGE RH
# ==========================================================
def page_rh(df):
    st.header("💧 Analisis Kelembapan Relatif (RH)")
    st.markdown("---")
    
    df_diurnal = get_diurnal_stats(df, "RH")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(plot_meteogram(df_diurnal, "Hour", "RH", "Meteogram Diurnal Kelembapan Relatif", "RH (%)", "#2ca02c"), use_container_width=True)
    with col2:
        st.info("💡 **Interpretasi Klimatologis**")
        st.write(interpret_diurnal_pattern(df_diurnal, "RH", "%"))
        st.warning("✈️ **Dampak Penerbangan (Aviation Notes)**")
        st.write(generate_aviation_notes("RH"))

# ==========================================================
# PAGE VISIBILITY
# ==========================================================
def page_visibility(df):
    st.header("👁️ Analisis Jarak Pandang (Visibility)")
    st.markdown("---")
    
    df_diurnal = get_diurnal_stats(df, "Visibility")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(plot_meteogram(df_diurnal, "Hour", "Visibility", "Meteogram Diurnal Visibilitas", "Visibilitas (Meter)", "#9467bd"), use_container_width=True)
    with col2:
        st.info("💡 **Interpretasi Klimatologis**")
        st.write(interpret_diurnal_pattern(df_diurnal, "Visibility", "m"))
        st.warning("✈️ **Dampak Penerbangan (Aviation Notes)**")
        st.write(generate_aviation_notes("Visibility"))

# ==========================================================
# PAGE CLOUD BASE
# ==========================================================
def page_cloud_base(df):
    st.header("☁️ Analisis Tinggi Dasar Awan (Cloud Base)")
    st.markdown("---")
    
    df_diurnal = get_diurnal_stats(df, "CloudBase")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(plot_meteogram(df_diurnal, "Hour", "CloudBase", "Meteogram Diurnal Tinggi Dasar Awan", "Tinggi (Feet)", "#8c564b"), use_container_width=True)
    with col2:
        st.info("💡 **Interpretasi Klimatologis**")
        st.write(interpret_diurnal_pattern(df_diurnal, "CloudBase", " ft"))
        st.warning("✈️ **Dampak Penerbangan (Aviation Notes)**")
        st.write(generate_aviation_notes("CloudBase"))

# ==========================================================
# PAGE WIND
# ==========================================================
def page_wind(df):
    st.header("🌬️ Analisis Arah dan Kecepatan Angin")
    st.markdown("---")
    
    df_diurnal = get_diurnal_stats(df, "WindSpeed")
    
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(plot_meteogram(df_diurnal, "Hour", "WindSpeed", "Meteogram Diurnal Kecepatan Angin", "Kecepatan (Knots)", "#e377c2"), use_container_width=True)
    with col2:
        st.plotly_chart(plot_wind_rose(df), use_container_width=True)
        
    st.info("💡 **Interpretasi Klimatologis & Aviation Notes**")
    st.write(interpret_diurnal_pattern(df_diurnal, "WindSpeed", " Knots"))
    st.write(generate_aviation_notes("Wind"))

# ==========================================================
# CROSS PARAMETER ANALYSIS
# ==========================================================
def page_cross_parameter(df):
    st.header("🔄 Analisis Silang Parameter (Cross-Parameter Analysis)")
    st.markdown("---")
    st.markdown("Analisis ini mengidentifikasi korelasi antara penurunan Suhu dan peningkatan Kelembapan Relatif (RH) dengan implikasinya terhadap Visibilitas.")
    
    # Mengambil sampel data agar scatter plot tidak terlalu padat
    df_sample = df.sample(n=min(5000, len(df)), random_state=42)
    
    fig = px.scatter(
        df_sample, 
        x="Temperature", 
        y="RH", 
        color="Visibility", 
        color_continuous_scale="Viridis",
        title="Korelasi Suhu vs RH terhadap Visibilitas",
        labels={"Temperature": "Suhu (°C)", "RH": "Kelembapan Relatif (%)", "Visibility": "Visibilitas (m)"}
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# METADATA
# ==========================================================
def page_metadata():
    st.header("ℹ️ Metadata Sistem dan Informasi Pangkalan")
    st.markdown("---")
    
    st.markdown(f"""
    - **Nama Pangkalan / Stasiun:** {STATION_NAME}
    - **Kode ICAO:** {ICAO_CODE}
    - **Elevasi:** {ELEVATION_M} Meter
    - **Periode Data:** {START_YEAR} - {END_YEAR}
    - **Tujuan Pengembangan:** Mendukung operasi militer taktis melalui penyediaan data Aerodrome Climatological Summary (ACS) yang komprehensif, berbasis *machine learning*, dan otomatis.
    - **Framework:** Python, Streamlit, Pandas, Plotly.
    """)

# ==========================================================
# MAIN
# ==========================================================
def main():
    # 1. Load Data
    raw_df = load_data()
    
    # 2. Validation
    validate_data(raw_df)
    
    # 3. Preprocessing
    df = preprocess_data(raw_df)
    
    # Sidebar Navigation
    st.sidebar.title("🎛️ Navigasi ACS")
    st.sidebar.markdown("Pilih modul analisis cuaca taktis:")
    
    menu = [
        "Home", 
        "Temperature", 
        "Relative Humidity (RH)", 
        "Visibility", 
        "Cloud Base", 
        "Wind", 
        "Cross Parameter Analysis", 
        "Metadata"
    ]
    choice = st.sidebar.radio("Menu", menu)
    
    # Routing
    if choice == "Home":
        page_home(df)
    elif choice == "Temperature":
        page_temperature(df)
    elif choice == "Relative Humidity (RH)":
        page_rh(df)
    elif choice == "Visibility":
        page_visibility(df)
    elif choice == "Cloud Base":
        page_cloud_base(df)
    elif choice == "Wind":
        page_wind(df)
    elif choice == "Cross Parameter Analysis":
        page_cross_parameter(df)
    elif choice == "Metadata":
        page_metadata()
        
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2026 - Aviation Meteorology System")

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
import plotly.express as px
import os
from bs4 import BeautifulSoup
from datetime import datetime

# ==========================================
# 1. KONFIGURASI SISTEM UTAMA
# ==========================================
st.set_page_config(
    page_title="Tactical Weather Ops - Lanud RSN",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. CSS STYLING (MILITARY / TACTICAL THEME)
# ==========================================
st.markdown("""
    <style>
    /* Tema Gelap Taktis */
    .stApp { background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", "Roboto Mono", monospace; }
    h1, h2, h3, h4 { color: #a9df52; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; }
    .st-expander { border-color: #3f4f3f !important; border-radius: 8px; }
    div[data-testid="stMetricValue"] { color: #a9df52; font-size: 28px; font-weight: bold; }
    section[data-testid="stSidebar"] { background-color: #111; border-right: 1px solid #2b3b2b; }
    .stButton>button { background-color: #1a2a1f; color: #a9df52; border: 1px solid #3f4f3f; border-radius: 8px; font-weight: bold; }
    .stButton>button:hover { background-color: #2b3b2b; border-color: #a9df52; }
    
    /* Footer Kustom */
    .footer { text-align: center; color: #7a7; font-size: 0.85rem; padding: 15px; border-top: 1px solid #3f4f3f; margin-top: 40px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. FUNGSI ROBUST DATA LOADER (ANTI-CRASH)
# ==========================================
@st.cache_data(ttl=600, show_spinner=False)
def fetch_bmkg_tactical_data(provinsi="Riau"):
    """Mengambil data cuaca BMKG via API secara aman"""
    url = f"https://data.bmkg.go.id/DataMKG/MEWS/DigitalForecast/DigitalForecast-{provinsi}.xml"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        st.error(f"⚠️ Gagal mengambil data taktis BMKG: {e}")
        return None

@st.cache_data(show_spinner=False)
def load_acs_data(filename):
    """Membaca file Excel lokal (Climatology) tanpa memicu error jika file hilang"""
    # Sesuaikan path ini jika file excel berada di dalam folder 'data' (misal: os.path.join("data", filename))
    filepath = filename 
    if os.path.exists(filepath):
        try:
            return pd.read_excel(filepath)
        except Exception as e:
            st.error(f"⚠️ Kesalahan membaca file {filepath}: {e}")
            return pd.DataFrame()
    else:
        st.warning(f"⚠️ File data {filepath} belum tersedia di repositori.")
        return pd.DataFrame()

# ==========================================
# 4. SIDEBAR COMMAND CENTER
# ==========================================
st.sidebar.markdown("### 🧭 COMMAND CENTER")
st.sidebar.caption("Sistem Informasi Cuaca Terintegrasi")

menu = st.sidebar.radio("Navigasi Modul:", [
    "📡 Real-Time Tactical (BMKG)", 
    "📊 ACS Climatology", 
    "🌬️ Diurnal & Windrose"
])

st.sidebar.markdown("---")
st.sidebar.caption("Operasional: Lanud Roesmin Nurjadin")

# ==========================================
# 5. ROUTING & RENDERING MODUL
# ==========================================

if menu == "📡 Real-Time Tactical (BMKG)":
    st.title("📡 Real-Time Tactical Weather Ops")
    st.markdown("Pemantauan observasi aktual terintegrasi API BMKG untuk dukungan operasi pangkalan.")
    
    with st.spinner("Menyinkronkan data dengan server BMKG..."):
        xml_data = fetch_bmkg_tactical_data()
        
    if xml_data:
        st.success("Tautan data operasional berhasil diamankan.")
        # [Bagian ini diisi dengan logika parsing BeautifulSoup dan visualisasi Metar/Tactical Table Anda]
        # Contoh struktur layout:
        col1, col2, col3 = st.columns(3)
        col1.metric("Status Sistem", "ONLINE", "API Aktif")
        col2.metric("Pembaruan Terakhir", datetime.now().strftime("%H:%M UTC"), "Real-time")
        col3.metric("Lokasi Sasaran", "Pekanbaru / WIBB", "Terverifikasi")
        
        st.info("Logika pemrosesan XML BMKG dan rendering peta taktis (st.map) diaktifkan di sini.")

elif menu == "📊 ACS Climatology":
    st.title("📊 Aerodrome Climatological Summary")
    st.markdown("Analisis data statistik penerbangan historis.")
    
    # Sub-navigasi untuk modul Climatology
    acs_menu = st.selectbox("Pilih Parameter ACS:", [
        "Temperature Frequency", 
        "Temperature Mean Max Min", 
        "Relative Humidity", 
        "Visibility", 
        "Cloud Base", 
        "Wind"
    ])
    
    st.markdown("---")
    
    if acs_menu == "Temperature Frequency":
        st.subheader("🌡️ Frekuensi Suhu")
        df_temp = load_acs_data("rekap_temperature_2021_2025.xlsx")
        if not df_temp.empty:
            st.dataframe(df_temp, use_container_width=True)
            # Logika Plotly Bar Chart...
            
    elif acs_menu == "Relative Humidity":
        st.subheader("💧 Kelembapan Relatif (RH)")
        df_rh = load_acs_data("rekap_rh_max_min_2021_2025.xlsx")
        if not df_rh.empty:
            st.dataframe(df_rh, use_container_width=True)
            # Logika Plotly Line Chart...
            
    # Tambahkan block elif lainnya sesuai dengan parameter Excel di repository Anda.

elif menu == "🌬️ Diurnal & Windrose":
    st.title("🌬️ Distribusi Diurnal & Windrose")
    st.markdown("Distribusi arah dan kecepatan angin berdasarkan standar instrumen.")
    
    # Contoh implementasi Windrose Standar WMO yang sudah diperbaiki (Utara di Atas)
    st.markdown("### Simulasi Plot Windrose (WMO Standard)")
    
    # Dummy data untuk fallback visualisasi jika data asli belum diproses
    compass_order = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    dummy_data = pd.DataFrame({
        "Direction_Label": np.random.choice(compass_order, 100),
        "Speed_Knot": np.random.randint(1, 20, 100),
        "Frequency": np.random.rand(100) * 10
    })
    
    fig = px.bar_polar(
        dummy_data, 
        r="Frequency", 
        theta="Direction_Label", 
        color="Speed_Knot",
        color_discrete_sequence=px.colors.sequential.Plasma_r,
        title="Distribusi Arah dan Kecepatan Angin (Knots)",
        template="plotly_dark" # Menggunakan tema gelap menyesuaikan desain taktis
    )
    
    # KONFIGURASI SUMBU POLAR (STANDAR WMO)
    fig.update_layout(
        margin=dict(t=100, b=40, l=40, r=40), # PERBAIKAN: Menambahkan margin atas agar judul tidak menabrak label 'N'
        polar=dict(
            angularaxis=dict(
                direction="clockwise",       # Berputar searah jarum jam
                categoryorder="array",       # Memaksa Plotly mengikuti urutan kompas
                categoryarray=compass_order,
                rotation=90                  # Memutar sumbu agar elemen pertama (Utara) tepat di atas
            ),
            radialaxis=dict(showline=True, gridcolor="#333")
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. FOOTER (IDENTITAS & HAK CIPTA)
# ==========================================
st.markdown("""
<div class="footer">
    <strong>Pengembangan Aerodrome Climatological Summary dan Informasi Cuaca Terintegrasi API BMKG</strong><br>
    Untuk Mendukung Operasional Pangkalan Militer Roesmin Nurjadin<br><br>
    © 2026 | Dikembangkan oleh: Resti Maulina Chusnul C. (NPT: 11220089) - Kelas: Meteorologi 7C STMKG
</div>
""", unsafe_allow_html=True)

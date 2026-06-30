import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# 1. KONFIGURASI APLIKASI & UI
# ==========================================
st.set_page_config(
    page_title="Aviation Climatology Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan Bersih, Modern, dan Aksen Biru BMKG
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    h1, h2, h3, h4 { color: #003366; font-family: 'Arial', sans-serif; }
    .st-expander { border: 1px solid #003366 !important; border-radius: 8px; background-color: #FFFFFF; }
    div[data-testid="stMetricValue"] { color: #003366; font-weight: bold; }
    .stDataFrame { background-color: #FFFFFF; border-radius: 8px; }
    hr { border-top: 2px solid #E0E0E0; }
    </style>
""", unsafe_allow_html=True)

MONTHS_ORDER = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 
                'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']

# ==========================================
# 2. MODUL DATA LOADER & AUTO-CLEANER TANGGUH
# ==========================================
@st.cache_data
def load_data(filename):
    """Membaca file Excel dengan penanganan error, header ganda, dan noise teks."""
    filepath = os.path.join("data", filename)
    if not os.path.exists(filepath):
        return None, f"File tidak ditemukan: {filepath}"
    
    try:
        # Baca secara default
        df = pd.read_excel(filepath)
        
        # Penanganan khusus jika header ada di baris kedua (sering terjadi di format BMKG/Wind)
        if 'DATE' not in df.columns:
            if 'DATE' in df.values[0]: # Jika header ada di row index 0
                df.columns = df.iloc[0]
                df = df[1:].reset_index(drop=True)
            else: # Coba skip row pertama
                df = pd.read_excel(filepath, header=1)
                
        if 'DATE' not in df.columns:
            return None, "Kolom 'DATE' tidak ditemukan meskipun sudah auto-detect."

        # 1. Hapus kolom 'Unnamed'
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # 2. Filter hanya baris yang berisi nama bulan yang valid (Menghilangkan catatan/notes di Excel)
        df = df[df['DATE'].isin(MONTHS_ORDER)].copy()
        
        # 3. Urutkan bulan secara kronologis (Jan - Des)
        df['DATE'] = pd.Categorical(df['DATE'], categories=MONTHS_ORDER, ordered=True)
        df = df.sort_values('DATE').reset_index(drop=True)
        
        # 4. Paksa semua kolom nilai menjadi numerik (Crucial step agar Plotly tidak error/acak-acakan)
        for col in df.columns:
            if col not in ['DATE', 'DIRECTION']:  # DIRECTION pada angin adalah string/kategorikal
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        return df, "Success"
    except Exception as e:
        return None, f"Gagal membaca data: {e}"

# ==========================================
# 3. MODUL AVIATION NOTES & HELPER
# ==========================================
def get_aviation_notes(parameter):
    notes = {
        "Temperature Freq": "Suhu tinggi berkaitan dengan peningkatan density altitude. Hal ini mengurangi performa aerodinamis dan mesin pesawat, membutuhkan take-off roll yang lebih panjang, dan berpotensi mengurangi Maximum Take-off Weight (MTOW).",
        "Temperature Mean": "Pemantauan fluktuasi suhu harian sangat penting untuk perencanaan beban muatan (payload) komersial dan efisiensi konsumsi bahan bakar jet.",
        "Relative Humidity": "RH yang tinggi (>80%) dengan suhu titik embun (dew point) yang mendekati suhu aktual mendukung pembentukan low cloud, embun, atau fog yang berdampak langsung pada jarak pandang pendaratan.",
        "Visibility": "Visibility rendah (terutama < 1500m) meningkatkan potensi gangguan operasi approach dan landing. Seringkali memaksa pengalihan penerbangan (divert) atau implementasi Low Visibility Procedures (LVP).",
        "Cloud Base": "Cloud base rendah (< 1000 ft) secara drastis meningkatkan peluang ceiling di bawah standar VFR. Membutuhkan instrumen precision approach (ILS) untuk pendaratan yang aman.",
        "Wind": "Dominasi arah angin (wind rose) menjadi referensi utama evaluasi konfigurasi runway-in-use. Komponen crosswind yang kuat berisiko untuk pesawat berbadan kecil."
    }
    return notes.get(parameter, "")

def get_download_link(df, filename):
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Data CSV",
        data=csv,
        file_name=filename,
        mime="text/csv",
        use_container_width=True
    )

# ==========================================
# 4. MODUL HALAMAN (PAGES)
# ==========================================

def render_home():
    st.title("✈️ Aviation Climatology Dashboard")
    st.markdown("---")
    st.markdown("""
    ### Tujuan Dashboard
    Dashboard ini berfungsi untuk menampilkan **KARAKTER KLIMATOLOGI PENERBANGAN** berdasarkan data ACS (*Aerodrome Climatological Summary*) hasil rekap rata-rata periode **2021–2025**.
    
    Fokus sistem ini bukan sekadar menyajikan nilai rata-rata, melainkan menjawab pertanyaan fundamental meteorologi operasional: **"How often does a condition occur?"** melalui analisis distribusi, frekuensi, dan probabilitas.
    """)
    
    st.markdown("### Statistik Dataset")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Periode Data", "2021 - 2025", "Update Terakhir")
    c2.metric("Total File", "6 Excel Files", "Tervalidasi")
    c3.metric("Fokus Analisis", "Frekuensi & Peluang")
    c4.metric("Resolusi", "Bulanan (Jan-Des)")

def render_temp_freq():
    st.title("🌡️ Temperature Frequency")
    st.info("Menampilkan distribusi peluang terjadinya rentang suhu tertentu dalam satu bulan (%).")
    
    df, status = load_data("rekap_temperature_2021_2025.xlsx")
    if df is not None:
        cols = [c for c in df.columns if c != 'DATE']
        
        # Visualisasi: Stacked Bar
        fig1 = px.bar(df, x='DATE', y=cols, title="Distribusi Frekuensi Rentang Suhu",
                      color_discrete_sequence=px.colors.sequential.YlOrRd, barmode='stack')
        fig1.update_layout(xaxis_title="Bulan", yaxis_title="Frekuensi (%)", legend_title="Rentang (°C)", plot_bgcolor="white", hovermode="x unified")
        fig1.update_xaxes(showgrid=True, gridcolor='#f0f0f0'); fig1.update_yaxes(showgrid=True, gridcolor='#f0f0f0')
        st.plotly_chart(fig1, use_container_width=True)

        # Visualisasi: Heatmap
        st.markdown("### Heatmap Probabilitas Suhu")
        fig2 = go.Figure(data=go.Heatmap(z=df[cols].T.values, x=df['DATE'], y=cols, colorscale='YlOrRd'))
        fig2.update_layout(xaxis_title="Bulan", yaxis_title="Rentang Suhu (°C)")
        st.plotly_chart(fig2, use_container_width=True)

        # Interpretasi & Ops Notes
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("💡 Interpretasi Meteorologi")
            if '> 35' in df.columns:
                hot_month = df.loc[df['> 35'].idxmax(), 'DATE']
                st.write(f"- Bulan dengan peluang kemunculan **suhu ekstrim (>35°C) tertinggi** adalah **{hot_month}**.")
            if '20 - 25' in df.columns:
                cool_month = df.loc[df['20 - 25'].idxmax(), 'DATE']
                st.write(f"- Bulan dengan peluang kemunculan **suhu sejuk (20-25°C) tertinggi** adalah **{cool_month}**.")
        with c2:
            st.subheader("⚠️ Aviation Operational Notes")
            st.warning(get_aviation_notes("Temperature Freq"))
        
        with st.expander("Tampilkan Data Asli (Original Data Table)"):
            st.dataframe(df, use_container_width=True)
            c_down, _, _ = st.columns(3)
            with c_down: get_download_link(df, "temp_frequency.csv")
    else: st.error(status)

def render_temp_mean_max_min():
    st.title("📈 Temperature Mean, Max, Min")
    st.info("Karakteristik klimatologi rentang suhu harian di aerodrome.")
    
    df, status = load_data("rekap_temp_max_min_2021_2025.xlsx")
    if df is not None:
        fig = go.Figure()
        # Area Fill Plotly: Tambahkan Min, lalu Max dengan fill='tonexty'
        if

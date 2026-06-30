import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# 1. CONFIGURATION & UI SETUP
# ==========================================
st.set_page_config(
    page_title="Aviation Climatology Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for BMKG Blue Accent & Clean Look
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    h1, h2, h3 { color: #0a4c8a; } /* BMKG Blue Accent */
    .st-expander { border-color: #0a4c8a !important; }
    div[data-testid="stMetricValue"] { color: #0a4c8a; }
    </style>
""", unsafe_allow_html=True)

# Fixed Month Order based on ACS Standards
MONTHS_ORDER = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 
                'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']

# ==========================================
# 2. DATA LOADER MODULE
# ==========================================
@st.cache_data
def load_data(filename):
    """Load and validate excel files robustly."""
    filepath = os.path.join("data", filename)
    if not os.path.exists(filepath):
        st.error(f"🚨 File tidak ditemukan: {filepath}. Pastikan file ada di folder 'data/'.")
        return None
    try:
        # Baca data dan paksa urutan bulan
        df = pd.read_excel(filepath)
        if 'DATE' in df.columns:
            df['DATE'] = pd.Categorical(df['DATE'], categories=MONTHS_ORDER, ordered=True)
            df = df.sort_values('DATE').reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"🚨 Gagal membaca file {filename}: {e}")
        return None

# ==========================================
# 3. INTERPRETATION & AVIATION NOTES MODULE
# ==========================================
def get_aviation_notes(parameter):
    notes = {
        "Temperature Freq": "Suhu tinggi (>30°C) menyebabkan penurunan densitas udara (High Density Altitude), yang membutuhkan *take-off roll* lebih panjang dan membatasi *Maximum Take-off Weight* (MTOW).",
        "Temperature Mean": "Variasi ekstrim suhu harian mempengaruhi perencanaan beban muatan dan performa daya dorong mesin pesawat.",
        "Relative Humidity": "RH yang secara konsisten tinggi (>80%) menandakan potensi tinggi pembentukan kabut (fog), embun, atau awan konvektif rendah saat dipicu oleh pemanasan permukaan.",
        "Visibility": "Visibility di bawah 1500m dapat memicu transisi ke kondisi terbang instrumen (IFR) dan menghambat operasi VFR.",
        "Cloud Base": "Ceiling rendah (Base <1000 ft) secara langsung mempengaruhi *decision height* saat *approach* dan dapat menyebabkan instruksi *go-around* jika visual ke runway tidak memadai.",
        "Wind": "Dominasi angin lintas (Crosswind) atau angin buritan (Tailwind) menentukan pemilihan arah *runway-in-use* dan batas aman operasi pesawat ringan."
    }
    return notes.get(parameter, "Catatan operasional tidak tersedia.")

# ==========================================
# 4. PLOTTING MODULE
# ==========================================
def plot_stacked_bar(df, x_col, y_cols, title, color_scale):
    fig = px.bar(df, x=x_col, y=y_cols, title=title, 
                 color_discrete_sequence=color_scale,
                 barmode='stack')
    fig.update_layout(xaxis_title="Bulan", yaxis_title="Frekuensi (%)", 
                      legend_title="Kategori", plot_bgcolor="white", hovermode="x unified")
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    return fig

def plot_line_meteogram(df, x_col, y_cols, title):
    fig = go.Figure()
    colors = ['#0a4c8a', '#d62728', '#2ca02c'] # Blue, Red, Green
    for idx, col in enumerate(y_cols):
        fig.add_trace(go.Scatter(x=df[x_col], y=df[col], mode='lines+markers', 
                                 name=col, line=dict(width=3, color=colors[idx % len(colors)])))
    fig.update_layout(title=title, xaxis_title="Bulan", yaxis_title="Nilai",
                      plot_bgcolor="white", hovermode="x unified")
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    return fig

# ==========================================
# 5. PAGE LOGIC & RENDER MODULES
# ==========================================
def render_home():
    st.title("✈️ Aviation Climatology Dashboard")
    st.markdown("""
    ### Tentang Dashboard
    Dashboard ini menyajikan **Karakter Klimatologi Penerbangan** berdasarkan data ACS (Aerodrome Climatological Summary) periode **2021–2025**. 
    
    Fokus utama sistem ini adalah menjawab: *"How often does a condition occur?"* dengan menampilkan distribusi probabilitas, frekuensi, dan interpretasi metorologi yang krusial untuk keselamatan dan efisiensi operasi penerbangan.
    """)
    col1, col2, col3 = st.columns(3)
    col1.metric("Periode Data", "2021 - 2025")
    col2.metric("Total Parameter", "6")
    col3.metric("Standar Referensi", "ICAO / WMO")

def render_temp_freq():
    st.header("🌡️ Temperature Frequency")
    df = load_data("rekap_temperature_2021_2025.xlsx")
    if df is not None:
        st.info("Karakteristik klimatologi probabilitas kemunculan suhu di bandara.")
        
        # Plot
        temp_cols = [col for col in df.columns if col not in ['DATE', 'Unnamed: 10']]
        fig = plot_stacked_bar(df, 'DATE', temp_cols, "Distribusi Frekuensi Suhu per Bulan", px.colors.sequential.Blues)
        st.plotly_chart(fig, use_container_width=True)
        
        # Interpretasi Otomatis
        st.subheader("💡 Auto-Interpretation")
        if '> 35' in df.columns:
            max_hot_month = df.loc[df['> 35'].idxmax(), 'DATE']
            st.write(f"- **Peluang Suhu Ekstrim (>35°C) Tertinggi:** Bulan **{max_hot_month}**.")
        if '25 - 30' in df.columns:
            max_ideal_month = df.loc[df['25 - 30'].idxmax(), 'DATE']
            st.write(f"- **Peluang Suhu 25-30°C Tertinggi:** Bulan **{max_ideal_month}**.")

        # Notes & Data
        st.warning(f"**Aviation Operational Notes:** {get_aviation_notes('Temperature Freq')}")
        
        with st.expander("Lihat Data Asli & Unduh"):
            st.dataframe(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="temp_freq.csv", mime="text/csv")

def render_rh():
    st.header("💧 Relative Humidity")
    df = load_data("rekap_rh_max_min_2021_2025.xlsx")
    if df is not None:
        st.info("Karakteristik kelembapan relatif (Mean, Max, Min).")
        
        fig = plot_line_meteogram(df, 'DATE', ['MEAN', 'MAX', 'MIN'], "Meteogram Relative Humidity (RH)")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("💡 Auto-Interpretation")
        max_rh_month = df.loc[df['MEAN'].idxmax(), 'DATE']
        min_rh_month = df.loc[df['MEAN'].idxmin(), 'DATE']
        st.write(f"- **Bulan Paling Lembap (Mean Tertinggi):** {max_rh_month}")
        st.write(f"- **Bulan Paling Kering (Mean Terendah):** {min_rh_month}")

        st.warning(f"**Aviation Operational Notes:** {get_aviation_notes('Relative Humidity')}")
        
        with st.expander("Lihat Data Asli & Unduh"):
            st.dataframe(df)
            st.download_button("Download CSV", data=df.to_csv(index=False).encode('utf-8'), 
                               file_name="rh_data.csv", mime="text/csv")

# ==========================================
# MAIN APP ROUTING
# ==========================================
def main():
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_BMKG.png", width=100) # Ganti dengan assets/logo.png
    st.sidebar.title("Navigasi ACS")
    menu = st.sidebar.radio("Pilih Parameter:", 
                            ["Home", 
                             "Temperature Frequency", 
                             "Temperature Mean Max Min", 
                             "Relative Humidity", 
                             "Visibility", 
                             "Cloud Base (HS)", 
                             "Wind"])
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Data Periode: 2021 - 2025")

    if menu == "Home":
        render_home()
    elif menu == "Temperature Frequency":
        render_temp_freq()
    elif menu == "Relative Humidity":
        render_rh()
    # Anda dapat mengembangkan fungsi render_temp_mean, render_vis, dll 
    # menggunakan pola yang sama persis dengan fungsi render_rh atau render_temp_freq di atas.
    else:
        st.info(f"Modul {menu} dalam tahap penyusunan menggunakan pola modular arsitektur.")

if __name__ == "__main__":
    main()

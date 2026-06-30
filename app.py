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
    h1, h2, h3 { color: #0a4c8a; font-weight: bold; }
    .st-expander { border-color: #0a4c8a !important; border-radius: 8px; }
    div[data-testid="stMetricValue"] { color: #0a4c8a; }
    .sidebar .sidebar-content { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

# Fixed Month Order based on ACS Standards
MONTHS_ORDER = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 
                'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
SHORT_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# ==========================================
# 2. DATA LOADER MODULE (ROBUST)
# ==========================================
@st.cache_data(show_spinner=False)
def load_data(filename):
    """Load and validate excel files robustly from root or data/ folder."""
    # Mengecek apakah file ada di root atau di dalam folder 'data'
    filepath = filename if os.path.exists(filename) else os.path.join("data", filename)
    
    if not os.path.exists(filepath):
        st.error(f"🚨 File tidak ditemukan: `{filename}`. Pastikan file sudah di-upload ke GitHub.")
        return None
    try:
        df = pd.read_excel(filepath)
        
        # Cari kolom waktu/bulan (biasanya DATE, BULAN, atau MONTH)
        date_col = None
        for col in df.columns:
            if str(col).upper() in ['DATE', 'BULAN', 'MONTH']:
                date_col = col
                break
                
        if date_col:
            # Standarisasi nama kolom ke 'DATE'
            df = df.rename(columns={date_col: 'DATE'})
            # Asumsi data berurutan dari Jan-Des. Jika tidak, paksa kategorikan.
            if len(df) == 12:
                df['DATE'] = SHORT_MONTHS  # Mempermudah visualisasi plot
            
        # Hapus kolom Unnamed hasil dari format excel yang kurang rapi
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        return df
    except Exception as e:
        st.error(f"🚨 Gagal membaca file {filename}: {e}")
        return None

# ==========================================
# 3. INTERPRETATION & AVIATION NOTES MODULE
# ==========================================
def get_aviation_notes(parameter):
    notes = {
        "Temperature Freq": "Suhu tinggi (>30°C) menyebabkan penurunan densitas udara (High Density Altitude). Hal ini mengurangi gaya angkat (lift) dan daya dorong mesin, sehingga membutuhkan *take-off roll* yang lebih panjang dan seringkali membatasi *Maximum Take-off Weight* (MTOW).",
        "Temperature Mean": "Variasi ekstrim suhu harian mempengaruhi perencanaan beban muatan penerbangan komersial dan kalkulasi performa daya dorong mesin pesawat pada fase *climb*.",
        "Relative Humidity": "RH yang secara konsisten tinggi (>80%) menandakan kandungan uap air yang jenuh. Saat dipicu oleh pemanasan permukaan atau pendinginan radiasi, ini berpotensi tinggi membentuk kabut (fog), embun, atau awan konvektif rendah yang membatasi jarak pandang.",
        "Visibility": "Visibility di bawah 1500m dapat memicu transisi aturan terbang dari VFR (Visual Flight Rules) ke kondisi terbang instrumen (IFR), serta memicu prosedur LVP (Low Visibility Procedures) di bandara.",
        "Cloud Base": "Ceiling yang rendah secara langsung mempengaruhi *decision height* saat melakukan *approach*. Jika batas awan lebih rendah dari ambang aman, pesawat berisiko melakukan *go-around* atau dialihkan (divert).",
        "Wind": "Dominasi arah angin lintas (Crosswind) atau angin buritan (Tailwind) menentukan pemilihan arah *runway-in-use*. Kecepatan angin ekstrem (Gusting) mempengaruhi kestabilan fase *final approach* dan *touchdown*."
    }
    return notes.get(parameter, "Catatan operasional tidak tersedia.")

def generate_auto_interpretation(df, plot_cols, param_name):
    st.subheader("💡 Interpretasi Otomatis Berdasarkan Data")
    st.write(f"Berikut adalah pembacaan otomatis dari data **{param_name}** hasil rata-rata periode 2021-2025:")
    
    if len(plot_cols) == 0:
        st.write("- Data numerik tidak cukup untuk diinterpretasi.")
        return

    # Interpretasi 2 kolom pertama (sebagai perwakilan kondisi)
    for col in plot_cols[:3]:
        max_val = df[col].max()
        max_month = df.loc[df[col] == max_val, 'DATE'].values[0]
        st.markdown(f"- Peluang kemunculan kondisi **{col}** tertinggi terjadi pada bulan **{max_month}** (Nilai: {max_val:.1f}).")

# ==========================================
# 4. PLOTTING MODULE
# ==========================================
def plot_heatmap(df, plot_cols, title, colorscale="Blues"):
    df_heat = df.set_index('DATE')[plot_cols].T
    fig = px.imshow(df_heat, text_auto=".1f", aspect="auto", 
                    color_continuous_scale=colorscale, title=title)
    fig.update_layout(plot_bgcolor="white", xaxis_title="Bulan", yaxis_title="Kategori")
    return fig

# ==========================================
# 5. PAGE LOGIC & RENDER MODULES
# ==========================================
def render_home():
    st.title("✈️ Aviation Climatology Dashboard")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        ### Tentang Dashboard
        Dashboard ini menyajikan **Karakter Klimatologi Penerbangan** berdasarkan data ACS (*Aerodrome Climatological Summary*) periode **2021–2025**. 
        
        Dashboard ini didesain khusus untuk menjawab pertanyaan operasional meteorologi:
        > *"How often does a condition occur?"*
        
        Fokus utama analisis meliputi frekuensi, probabilitas, dan distribusi kejadian cuaca yang krusial untuk keselamatan (safety) dan efisiensi operasi penerbangan (efficiency), mengacu pada standar regulasi ICAO dan WMO.
        """)
    with col2:
        st.info("**Statistik Dashboard**")
        st.write("📅 **Periode:** 2021 - 2025")
        st.write("📂 **Total File Data:** 6")
        st.write("📊 **Visualisasi:** Plotly Interaktif")
        st.write("⚙️ **Modul Interpretasi:** Aktif")

def render_generic_page(title, filename, param_key, chart_types=['bar'], colorscale="Blues"):
    st.title(f"📊 {title}")
    st.markdown("---")
    
    df = load_data(filename)
    if df is not None:
        plot_cols = [c for c in df.columns if c != 'DATE']
        
        # Tabs for Visualizations
        tabs = st.tabs(["Meteogram Chart", "Heatmap Analysis", "Data & Interpretasi"])
        
        with tabs[0]:
            if 'bar' in chart_types:
                fig = px.bar(df, x='DATE', y=plot_cols, title=f"Distribusi Frekuensi Bulanan - {title}", 
                             barmode='stack', color_discrete_sequence=px.colors.sequential.Blues_r)
            elif 'line' in chart_types:
                fig = go.Figure()
                colors = ['#0a4c8a', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd']
                for idx, col in enumerate(plot_cols):
                    fig.add_trace(go.Scatter(x=df['DATE'], y=df[col], mode='lines+markers', 
                                             name=col, line=dict(width=3, color=colors[idx % len(colors)])))
                fig.update_layout(title=f"Tren Bulanan - {title}", hovermode="x unified")
            
            fig.update_layout(xaxis_title="Bulan", yaxis_title="Nilai / Probabilitas", plot_bgcolor="white")
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
            st.plotly_chart(fig, use_container_width=True)
            
        with tabs[1]:
            st.info("Heatmap memudahkan identifikasi pola konsentrasi bulan dengan probabilitas tertinggi.")
            fig_heat = plot_heatmap(df, plot_cols, f"Konsentrasi Probabilitas - {title}", colorscale)
            st.plotly_chart(fig_heat, use_container_width=True)

        with tabs[2]:
            col1, col2 = st.columns([1.5, 1])
            with col1:
                generate_auto_interpretation(df, plot_cols, title)
                st.warning(f"**Aviation Operational Notes:** {get_aviation_notes(param_key)}")
            with col2:
                st.markdown("#### Original Data Table")
                st.dataframe(df, use_container_width=True, hide_index=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Download CSV", data=csv, 
                                   file_name=f"{filename.split('.')[0]}.csv", mime="text/csv",
                                   use_container_width=True)

# ==========================================
# MAIN APP ROUTING
# ==========================================
def main():
    # Sidebar
    st.sidebar.markdown("## 🧭 Navigasi ACS")
    st.sidebar.caption("Data Periode: 2021 - 2025")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.radio("Pilih Parameter Analisis:", [
        "Home", 
        "Temperature Frequency", 
        "Temperature Mean Max Min", 
        "Relative Humidity", 
        "Visibility", 
        "Cloud Base (HS)", 
        "Wind"
    ])
    
    st.sidebar.markdown("---")
    st.sidebar.info("Aviation Climatology Dashboard © 2026")

    # Routing dengan percabangan (if-elif) yang sudah diperbaiki sintaksnya
    if menu == "Home":
        render_home()
    elif menu == "Temperature Frequency":
        render_generic_page("Temperature Frequency", "rekap_temperature_2021_2025.xlsx", 
                            "Temperature Freq", chart_types=['bar'], colorscale="Reds")
    elif menu == "Temperature Mean Max Min":
        render_generic_page("Temperature Mean, Max, Min", "rekap_temp_max_min_2021_2025.xlsx", 
                            "Temperature Mean", chart_types=['line'], colorscale="Reds")
    elif menu == "Relative Humidity":
        render_generic_page("Relative Humidity", "rekap_rh_max_min_2021_2025.xlsx", 
                            "Relative Humidity", chart_types=['line'], colorscale="YlGnBu")
    elif menu == "Visibility":
        render_generic_page("Visibility (Jarak Pandang)", "rekap_visibility_2021_2025.xlsx", 
                            "Visibility", chart_types=['bar'], colorscale="Viridis")
    elif menu == "Cloud Base (HS)":
        render_generic_page("Cloud Base (Ceiling)", "rekap_hs_2021_2025.xlsx", 
                            "Cloud Base", chart_types=['bar'], colorscale="Blues")
    elif menu == "Wind":
        render_generic_page("Wind (Angin Permukaan)", "rekap_wind_2021_2025.xlsx", 
                            "Wind", chart_types=['bar'], colorscale="Cividis")

if __name__ == "__main__":
    main()

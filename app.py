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

st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    h1, h2, h3 { color: #003366; font-weight: bold; }
    .st-expander { border-color: #003366 !important; border-radius: 8px; }
    div[data-testid="stMetricValue"] { color: #003366; }
    .sidebar .sidebar-content { background-color: #FFFFFF; box-shadow: 2px 0 5px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True)

# Urutan Bulan Baku sesuai instruksi (Jan - Des)
BAKU_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

# ==========================================
# 2. ROBUST DATA LOADER MODULE
# ==========================================
@st.cache_data(show_spinner=False)
def load_data(filename):
    """
    Membaca data Excel dengan mendeteksi otomatis letak header yang berantakan 
    dan mengkonversi string menjadi numerik tanpa merubah nilai.
    """
    filepath = filename if os.path.exists(filename) else os.path.join("data", filename)
    
    if not os.path.exists(filepath):
        st.error(f"🚨 File tidak ditemukan: `{filename}`. Pastikan nama file di GitHub sesuai.")
        return None
        
    try:
        # 1. Baca mentah tanpa header untuk mencari lokasi header sebenarnya
        raw_df = pd.read_excel(filepath, header=None)
        
        # 2. Auto-detect Header Row (Cari baris yang punya kata DATE, BULAN, atau MONTH)
        header_idx = 0
        for i in range(min(15, len(raw_df))):
            row_vals = [str(x).upper().strip() for x in raw_df.iloc[i].fillna('')]
            if any(c in row_vals for c in ['DATE', 'BULAN', 'MONTH', 'JAN', 'JANUARI', 'JANUARY']):
                # Jika baris ini berisi bulan 'JAN', headernya pasti di baris sebelumnya
                if 'JAN' in row_vals or 'JANUARI' in row_vals or 'JANUARY' in row_vals:
                    header_idx = max(0, i - 1)
                else:
                    header_idx = i
                break
        
        # 3. Tetapkan header dan buang baris di atasnya
        df = raw_df.iloc[header_idx+1:].copy()
        df.columns = raw_df.iloc[header_idx].astype(str).str.strip()
        
        # 4. Bersihkan kolom kotor (Unnamed / NaN)
        df = df.loc[:, df.columns.notna()]
        df = df.loc[:, ~df.columns.str.lower().str.contains('nan|unnamed')]
        
        # 5. Cari dan standardisasi kolom Bulan/Waktu menjadi 'DATE'
        date_col = None
        for col in df.columns:
            if str(col).upper() in ['DATE', 'BULAN', 'MONTH']:
                date_col = col
                break
        if date_col:
            df = df.rename(columns={date_col: 'DATE'})
        else:
            df = df.rename(columns={df.columns[0]: 'DATE'}) # Fallback kolom pertama

        # 6. Filter hanya data bulanan (Membuang baris 'Total', 'Average', 'Tahunan' di bawah tabel)
        valid_months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'MEI', 'JUN', 'JUL', 'AUG', 'AGU', 'SEP', 'OCT', 'OKT', 'NOV', 'DEC', 'DES']
        df['TEMP_DATE'] = df['DATE'].astype(str).str.upper().str.strip().str[:3]
        df = df[df['TEMP_DATE'].isin(valid_months)].copy()
        df = df.drop(columns=['TEMP_DATE'])
        
        # 7. Paksa Urutan Bulan Baku (Jan - Des)
        if len(df) >= 12:
            df['DATE'] = BAKU_MONTHS[:len(df)]
        
        # 8. Konversi data kolom ke Numerik murni agar Plotly tidak error
        plot_cols = [c for c in df.columns if c != 'DATE']
        for col in plot_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df.reset_index(drop=True)
        
    except Exception as e:
        st.error(f"🚨 Gagal memproses file {filename}: {e}")
        return None

# ==========================================
# 3. AVIATION NOTES & INTERPRETATION MODULE
# ==========================================
def get_aviation_notes(parameter):
    notes = {
        "Temperature Freq": "Suhu tinggi berkaitan dengan peningkatan density altitude. Ini menurunkan performa daya angkat pesawat, menuntut take-off roll lebih panjang, dan membatasi Maximum Take-off Weight (MTOW).",
        "Temperature Mean": "Pemahaman fluktuasi rata-rata suhu harian sangat vital bagi flight dispatcher untuk kalkulasi fuel burn dan manajemen beban muatan yang efisien.",
        "Relative Humidity": "RH tinggi (mendekati 100%) mendukung probabilitas pembentukan embun, kabut radiasi, atau low clouds saat terjadi pendinginan nokturnal, berdampak langsung pada jarak pandang.",
        "Visibility": "Visibility rendah meningkatkan potensi gangguan operasi approach dan landing, seringkali memaksa pemberlakuan prosedur IFR (Instrument Flight Rules) dan Low Visibility Procedures (LVP).",
        "Cloud Base": "Cloud base (ceiling) yang sangat rendah berisiko melanggar standar Decision Height (DH). Hal ini meningkatkan peluang missed approach atau pengalihan rute (divert) ke bandara alternatif.",
        "Wind": "Distribusi dominan arah dan kecepatan angin menjadi referensi mutlak evaluasi konfigurasi runway-in-use. Kecepatan angin tinggi memicu windshear/crosswind yang membahayakan fase final approach."
    }
    return notes.get(parameter, "Catatan operasional tidak tersedia.")

def generate_auto_interpretation(df, plot_cols, param_name):
    st.subheader("💡 Interpretasi Karakter Klimatologi")
    st.markdown("Berdasarkan hasil analisis data secara otomatis:")
    
    if len(plot_cols) == 0:
        st.write("- Tidak cukup data untuk diinterpretasikan.")
        return

    # Mencari nilai tertinggi dari beberapa parameter ekstrim/dominan
    for col in plot_cols[:3]: # Mengambil maksimal 3 kolom pertama sebagai sampel interpretasi
        max_val = df[col].max()
        max_month = df.loc[df[col] == max_val, 'DATE'].values[0]
        if max_val > 0:
            st.write(f"- Peluang kemunculan frekuensi kondisi **{col}** tertinggi terjadi pada bulan **{max_month}** (Nilai probabilitas/frekuensi: {max_val}).")

# ==========================================
# 4. DASHBOARD PAGES
# ==========================================
def render_home():
    st.title("✈️ Aviation Climatology Dashboard")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        ### Deskripsi & Tujuan
        Dashboard operasional klimatologi penerbangan ini memvisualisasikan data **ACS (Aerodrome Climatological Summary)** rata-rata periode **2021–2025**. 
        
        Dashboard ini didesain tidak hanya untuk menyajikan angka, melainkan menjawab krusialitas operasional meteorologi: 
        **"How often does a condition occur?"** (Berapa sering suatu kondisi terjadi?).
        
        Fokus analisis:
        * Frekuensi & Probabilitas Kejadian
        * Distribusi Musiman
        * Interpretasi Meteorologis Otomatis
        * Implikasi Operasional Penerbangan
        """)
    with col2:
        st.info("📊 **Statistik ACS Dashboard**")
        st.write("📅 **Periode Data:** 2021 - 2025")
        st.write("📂 **Total File / Parameter:** 6 Parameter")
        st.write("📈 **Data Integrity:** Original (No Smoothing)")
        st.write("⚙️ **Modul Engine:** Automated Parsing")

def render_generic_page(title, filename, param_key, chart_type='bar', colorscale="Blues"):
    st.title(f"{title}")
    st.markdown(f"*{get_aviation_notes(param_key)}*")
    st.markdown("---")
    
    df = load_data(filename)
    if df is not None:
        plot_cols = [c for c in df.columns if c != 'DATE']
        
        # 1. Main Visualizations (Container)
        col_chart, col_metric = st.columns([3, 1])
        
        with col_chart:
            st.markdown("### 📈 Interactive Meteogram")
            if chart_type == 'bar':
                fig = px.bar(df, x='DATE', y=plot_cols, barmode='stack', 
                             color_discrete_sequence=px.colors.sequential.__dict__[colorscale])
            else: # Line chart
                fig = go.Figure()
                colors = ['#003366', '#d62728', '#2ca02c', '#ff7f0e']
                for idx, col in enumerate(plot_cols):
                    fig.add_trace(go.Scatter(x=df['DATE'], y=df[col], mode='lines+markers', 
                                             name=col, line=dict(width=3, color=colors[idx % len(colors)])))
            
            fig.update_layout(xaxis_title="Bulan", yaxis_title="Nilai", 
                              plot_bgcolor="white", hovermode="x unified", legend_title="Parameter")
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8')
            st.plotly_chart(fig, use_container_width=True)

        with col_metric:
            st.markdown("### 🌡️ Heatmap Profil")
            df_heat = df.set_index('DATE')[plot_cols].T
            fig_heat = px.imshow(df_heat, text_auto=".1f", aspect="auto", color_continuous_scale=colorscale)
            fig_heat.update_layout(plot_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_heat, use_container_width=True)
            
        # 2. Insights & Original Data Table
        st.markdown("---")
        col_insight, col_data = st.columns([1, 1])
        
        with col_insight:
            generate_auto_interpretation(df, plot_cols, title)
            st.success("✅ **Operational Note:** " + get_aviation_notes(param_key))
            
        with col_data:
            st.markdown("### 🗃️ Original Data Table")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Download Buttons
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="⬇️ Download CSV", data=csv, 
                               file_name=f"{filename.replace('.xlsx', '')}.csv", mime="text/csv",
                               use_container_width=True)

# ==========================================
# 5. MAIN ROUTER
# ==========================================
def main():
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_BMKG.png", width=80)
    st.sidebar.markdown("## 🧭 Navigasi Menu")
    st.sidebar.caption("Data Rata-Rata: 2021 - 2025")
    
    menu = st.sidebar.radio("", [
        "Home", 
        "Temperature Frequency", 
        "Temperature Mean Max Min", 
        "Relative Humidity", 
        "Visibility", 
        "Cloud Base (HS)", 
        "Wind"
    ])
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Aviation Climatology Dashboard © 2026")

    # Routing
    if menu == "Home":
        render_home()
    elif menu == "Temperature Frequency":
        render_generic_page("🌡️ Temperature Frequency", "rekap_temperature_2021_2025.xlsx", "Temperature Freq", 'bar', "Reds")
    elif menu == "Temperature Mean Max Min":
        render_generic_page("📈 Temperature Mean Max Min", "rekap_temp_max_min_2021_2025.xlsx", "Temperature Mean", 'line', "Reds")
    elif menu == "Relative Humidity":
        render_generic_page("💧 Relative Humidity", "rekap_rh_max_min_2021_2025.xlsx", "Relative Humidity", 'line', "Teal")
    elif menu == "Visibility":
        render_generic_page("🌫️ Visibility", "rekap_visibility_2021_2025.xlsx", "Visibility", 'bar', "Greens")
    elif menu == "Cloud Base (HS)":
        render_generic_page("☁️ Cloud Base (Ceiling)", "rekap_hs_2021_2025.xlsx", "Cloud Base", 'bar', "Blues")
    elif menu == "Wind":
        render_generic_page("🌬️ Wind", "rekap_wind_2021_2025.xlsx", "Wind", 'bar', "Purples")

if __name__ == "__main__":
    main()

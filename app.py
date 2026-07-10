import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ==========================================
# 1. CONFIGURATION & UI SETUP
# ==========================================
st.set_page_config(
    page_title="Aviation Weather Statistics",
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

BAKU_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

# ==========================================
# 2. ROBUST DATA LOADER MODULE
# ==========================================
@st.cache_data(show_spinner=False)
def load_data(filename):
    """
    Membaca data secara dinamis dengan algoritma Smart Vertical Header Scanner.
    Kebal terhadap merged cells Excel untuk mencegah hilangnya T MAX, T MIN, dsb.
    """
    filepath = filename if os.path.exists(filename) else os.path.join("data", filename)
    
    if not os.path.exists(filepath):
        st.error(f"🚨 File tidak ditemukan: `{filename}`. Pastikan nama file sesuai di repositori.")
        return None
        
    try:
        raw_df = pd.read_excel(filepath, header=None, engine='openpyxl')
        
        # 1. Cari Index Baris Pertama yang Mengandung Data Bulan
        data_start_idx = 0
        for i in range(min(15, len(raw_df))):
            row_vals = [str(x).upper().strip() for x in raw_df.iloc[i].fillna('')]
            if 'JAN' in row_vals or 'JANUARI' in row_vals or 'JANUARY' in row_vals:
                data_start_idx = i
                break
        
        df = raw_df.iloc[data_start_idx:].copy().reset_index(drop=True)
        
        # 2. Ekstrak Header Cerdas 
        if data_start_idx > 0:
            new_cols = []
            for col_idx in range(len(raw_df.columns)):
                col_name = ""
                for r in range(data_start_idx - 1, -1, -1):
                    val = str(raw_df.iloc[r, col_idx]).strip()
                    if val.lower() not in ['nan', 'none', ''] and not val.lower().startswith('unnamed'):
                        col_name = val
                        break
                if not col_name:
                    col_name = f"DropMe_{col_idx}"
                new_cols.append(col_name)
            df.columns = new_cols
        
        # 3. Identifikasi Kolom DATE Secara Absolut
        date_col = None
        if not df.empty:
            for col in df.columns:
                first_val = str(df[col].iloc[0]).upper().strip()
                if first_val in ['JAN', 'JANUARI', 'JANUARY']:
                    date_col = col
                    break
        
        if date_col:
            df = df.rename(columns={date_col: 'DATE'})
        else:
            df = df.rename(columns={df.columns[0]: 'DATE'})

        # 4. Buang kolom kosong
        valid_cols = [c for c in df.columns if not str(c).startswith('DropMe_')]
        df = df[valid_cols]

        # 5. Standarisasi Format Bulan
        valid_months_map = {
            'JAN': 'Jan', 'FEB': 'Feb', 'MAR': 'Mar', 'APR': 'Apr', 'MAY': 'Mei', 'MEI': 'Mei',
            'JUN': 'Jun', 'JUL': 'Jul', 'AUG': 'Agu', 'AGU': 'Agu', 'SEP': 'Sep', 'OCT': 'Okt',
            'OKT': 'Okt', 'NOV': 'Nov', 'DEC': 'Des', 'DES': 'Des'
        }
        
        df['TEMP_DATE'] = df['DATE'].astype(str).str.upper().str.strip().str[:3]
        df = df[df['TEMP_DATE'].isin(valid_months_map.keys())].copy()
        
        df = df.drop_duplicates(subset=['TEMP_DATE'], keep='first')
        df['DATE'] = df['TEMP_DATE'].map(valid_months_map)
        df = df.drop(columns=['TEMP_DATE'])
        
        df['DATE_CAT'] = pd.Categorical(df['DATE'], categories=BAKU_MONTHS, ordered=True)
        df = df.sort_values('DATE_CAT').drop(columns=['DATE_CAT']).reset_index(drop=True)
        
        # 6. Casting Data Numerik Secara Aman
        for col in df.columns:
            if col == 'DATE':
                continue
            elif str(col).upper() == 'DIRECTION':
                df[col] = df[col].astype(str) 
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
        
    except Exception as e:
        st.error(f"🚨 Gagal memproses file {filename}: {str(e)}")
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

def generate_auto_interpretation(df, plot_cols, title, param_key):
    """
    Menghasilkan interpretasi meteorologi berdasarkan hukum kausalitas 
    fisika atmosfer serta regulasi operasional ICAO dan WMO.
    """
    st.subheader("💡 Interpretasi Kausalitas Operasional (WMO & ICAO)")
    
    if not plot_cols or df.empty:
        st.write("- Tidak cukup data untuk diinterpretasikan secara otomatis.")
        return

    # Ekstraksi Data Dominan untuk Fakta Aktual
    max_val = -float('inf')
    max_col_name = ""
    max_month = ""
    
    for col in plot_cols:
        col_max = df[col].max()
        if col_max > max_val:
            max_val = col_max
            max_col_name = col
            # Ambil bulan tempat nilai max terjadi (jika ada lebih dari 1, ambil yang pertama)
            max_months_series = df.loc[df[col] == col_max, 'DATE'].values
            if len(max_months_series) > 0:
                max_month = max_months_series[0]

    if max_val > 0:
        st.markdown(f"**Fakta Analitik:** Kejadian atau frekuensi dominan tercatat pada profil **{max_col_name}** di bulan **{max_month}** (Nilai: {max_val}).")
    
    st.markdown("**Analisis Sebab-Akibat Meteorologis & Dampak Penerbangan:**")
    
    # Kausalitas Spesifik Parameter
    if param_key in ["Temperature Freq", "Temperature Mean"]:
        st.markdown("""
        * **Sebab (Fisika Atmosfer):** Pemanasan permukaan radiatif yang intensif meningkatkan suhu lingkungan melebihi kondisi atmosfer standar (ISA).
        * **Akibat (Kondisi Udara):** Kerapatan udara (*air density*) di sekitar pangkalan udara menurun secara drastis, memicu lonjakan eksponensial pada *Density Altitude* (WMO No. 732).
        * **Dampak Operasional:** Kurangnya massa molekul udara mengurangi gaya angkat (*lift*) sayap pesawat dan dorongan mesin. Sesuai ICAO Doc 8168, kondisi ini krusial bagi pesawat kargo atau militer karena menuntut jarak *take-off roll* yang jauh lebih panjang, dan berpotensi memaksa pembatasan *Maximum Take-off Weight* (MTOW) demi menjaga jarak aman rintangan (*obstacle clearance*).
        """)
    elif param_key == "Relative Humidity":
        st.markdown("""
        * **Sebab (Fisika Atmosfer):** Akumulasi uap air masif (RH > 90%) yang diikuti oleh fase pendinginan nokturnal atau datangnya massa udara dingin dari pergerakan awan konvektif.
        * **Akibat (Kondisi Udara):** Temperatur lingkungan anjlok hingga menyentuh titik embun (*dew point temperature*). Proses ini melepaskan panas laten kondensasi dan mengubah uap air menjadi titik-titik air tersuspensi di lapisan batas atmosfer (WMO No. 731).
        * **Dampak Operasional:** Perubahan fasa ini menghasilkan fenomena *mist*, *fog*, atau fraksi awan rendah yang secara instan mendegradasi jarak pandang visual pilot, berpotensi menunda peluncuran operasi terbang visual (VFR).
        """)
    elif param_key == "Visibility":
        st.markdown("""
        * **Sebab (Fisika Atmosfer):** Konsentrasi partikel penghalang pandangan—seperti kabut, presipitasi curah hujan intens (contohnya dari sel badai/MCS), atau aerosol—di sepanjang jalur penerbangan.
        * **Akibat (Kondisi Udara):** Terjadinya peredaman (atenuasi) optik berupa hamburan dan penyerapan cahaya di lapisan udara permukaan.
        * **Dampak Operasional:** Penurunan jarak pandang horizontal mengancam fase kritis pendaratan. Merujuk ICAO Annex 3, ketika visibilitas turun di bawah ambang batas minimum fasilitas bandara, prosedur pendekatan instrumen presisi atau *Low Visibility Procedures* (LVP) harus diaktifkan untuk mencegah *Controlled Flight Into Terrain* (CFIT).
        """)
    elif param_key == "Cloud Base":
        st.markdown("""
        * **Sebab (Fisika Atmosfer):** Ketidakstabilan atmosfer taktis yang memicu aliran updraft kuat, mengangkut uap air ke atas hingga melewati *Lifting Condensation Level* (LCL) dan membentuk awan konvektif dengan dasar yang rendah.
        * **Akibat (Kondisi Udara):** Lapisan dasar awan (*cloud ceiling*) menutupi area aerodrome, memblokir kontak visual vertikal dan oblik dari ruang udara di atasnya (WMO No. 732).
        * **Dampak Operasional:** *Ceiling* di bawah batas minimum *Decision Altitude/Height* (DA/H) membuat pilot kehilangan referensi visual terhadap landasan pacu. Menurut ICAO Doc 9365, ketiadaan landasan pada ketinggian ini memaksa pilot mengeksekusi *missed approach* atau pengalihan (*divert*) pendaratan demi keselamatan.
        """)
    elif param_key == "Wind":
        st.markdown("""
        * **Sebab (Fisika Atmosfer):** Perbedaan tekanan lokal yang ekstrem atau *downdraft/outflow* beringas dari sistem cuaca skala meso (seperti *squall lines*) di sekitar wilayah pangkalan.
        * **Akibat (Kondisi Udara):** Fluktuasi vektor angin yang radikal. Ini menciptakan angin permukaan yang sangat kencang, pergeseran arah tiba-tiba (*windshear*), atau *crosswind* yang tajam memotong garis landasan.
        * **Dampak Operasional:** Angin lintang yang dominan dan agresif melampaui batasan struktural komponen ekor vertikal pesawat, memicu masalah stabilitas yaw. ICAO Annex 14 mewajibkan data arah angin (*windrose*) sebagai parameter primer bagi ATC untuk menetapkan *runway-in-use* dan menjamin pendaratan *headwind* yang aman.
        """)
    else:
        st.markdown("* Interpretasi otomatis untuk sistem operasional standar belum terdefinisi.*")

# ==========================================
# 4. DASHBOARD PAGES & VISUALIZATIONS
# ==========================================
def render_generic_page(title, filename, param_key, chart_type='bar', colorscale="Rainbow", legend_title="Kategori"):
    st.title(f"{title}")
    st.markdown(f"*{get_aviation_notes(param_key)}*")
    st.markdown("---")
    
    df = load_data(filename)
    if df is not None and not df.empty:
        plot_cols = [c for c in df.columns if str(c).upper() not in ['DATE', 'DIRECTION']]
        
        col_chart, col_metric = st.columns([3, 1])
        
        mejiku_colors = px.colors.sample_colorscale("Rainbow", [i/(len(plot_cols)-1) if len(plot_cols)>1 else 1 for i in range(len(plot_cols))])
        
        with col_chart:
            st.markdown("### 📈 Interactive Meteogram")
            if chart_type == 'bar':
                fig = px.bar(
                    df, x='DATE', y=plot_cols, barmode='group', 
                    color_discrete_sequence=mejiku_colors,
                    labels={"variable": legend_title, "value": "Nilai / Frekuensi", "DATE": "Bulan"}
                )
            else: 
                fig = go.Figure()
                for idx, col in enumerate(plot_cols):
                    fig.add_trace(go.Scatter(
                        x=df['DATE'], y=df[col], mode='lines+markers', 
                        name=str(col), line=dict(width=3, color=mejiku_colors[idx % len(mejiku_colors)])
                    ))
            
            fig.update_layout(
                xaxis_title="Bulan", 
                yaxis_title="Frekuensi / Nilai", 
                plot_bgcolor="white", 
                hovermode="x unified",
                legend_title_text=legend_title
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8')
            st.plotly_chart(fig, width="stretch")

        with col_metric:
            st.markdown("### 🌡️ Heatmap Profil")
            df_heat = df.set_index('DATE')[plot_cols].T
            fig_heat = px.imshow(
                df_heat, text_auto=".1f", aspect="auto", 
                color_continuous_scale="Rainbow",
                labels={"x": "Bulan", "y": legend_title, "color": "Nilai"}
            )
            fig_heat.update_layout(plot_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_heat, width="stretch")
            
        st.markdown("---")
        col_insight, col_data = st.columns([1, 1])
        
        with col_insight:
            generate_auto_interpretation(df, plot_cols, title, param_key)
            st.success("✅ **Operational Note:** " + get_aviation_notes(param_key))
            
        with col_data:
            st.markdown("### 🗃️ Original Data Table")
            st.dataframe(df, width="stretch", hide_index=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="⬇️ Download CSV", data=csv, 
                               file_name=f"{filename.replace('.xlsx', '')}.csv", mime="text/csv",
                               width="stretch")
    else:
        st.warning("⚠️ Data kosong atau gagal diolah. Pastikan file tersedia.")

def render_wind_page():
    st.title("🌬️ Wind Analysis (Arah & Kecepatan)")
    st.markdown(f"*{get_aviation_notes('Wind')}*")
    st.markdown("---")
    
    df = load_data("rekap_wind_2021_2025.xlsx")
    if df is not None and not df.empty:
        dir_cols = [c for c in df.columns if '-' in str(c) and len(str(c).split('-')) == 3]
        speed_cols = [c for c in df.columns if c not in dir_cols and str(c).upper() not in ['DATE', 'CALM', 'DIRECTION']]
        
        st.markdown("### 📈 Unified Interactive Windrose & Speed Distribution")
        
        fig_wind = make_subplots(
            rows=1, cols=2, 
            specs=[[{'type': 'polar'}, {'type': 'xy'}]],
            subplot_titles=("Windrose (Distribusi Arah)", "Distribusi Kecepatan Angin (Bulan)"),
            horizontal_spacing=0.15
        )

        if dir_cols:
            avg_dir = df[dir_cols].mean().reset_index()
            avg_dir.columns = ['Arah', 'Frekuensi']
            
            fig_wind.add_trace(
                go.Barpolar(
                    r=avg_dir['Frekuensi'],
                    theta=avg_dir['Arah'],
                    marker_color=avg_dir['Frekuensi'],
                    marker_colorscale='Rainbow', 
                    name="Arah Angin (Avg)",
                    showlegend=False
                ),
                row=1, col=1
            )

        if speed_cols:
            mejiku_colors = px.colors.sample_colorscale("Rainbow", [i/(len(speed_cols)-1) if len(speed_cols)>1 else 1 for i in range(len(speed_cols))])
            
            for idx, col in enumerate(speed_cols):
                fig_wind.add_trace(
                    go.Bar(
                        x=df['DATE'], 
                        y=df[col], 
                        name=f"{col} Kts",
                        marker_color=mejiku_colors[idx]
                    ),
                    row=1, col=2
                )
        
        fig_wind.update_layout(
            barmode='group', 
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=True),
                angularaxis=dict(direction="clockwise")
            ),
            legend_title_text="Kategori Kecepatan",
            height=500,
            plot_bgcolor="white",
            margin=dict(t=100, b=50, l=50, r=50)
        )
        
        for ann in fig_wind.layout.annotations:
            ann.y = 1.12
            ann.font = dict(size=14)

        fig_wind.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8', row=1, col=2)
        fig_wind.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8', title_text="Frekuensi", row=1, col=2)
        
        st.plotly_chart(fig_wind, width="stretch")

        st.markdown("### 🌡️ Heatmap Profil Angin")
        col_heat1, col_heat2 = st.columns(2)
        
        with col_heat1:
            if dir_cols:
                st.markdown("**Distribusi Arah Angin**")
                df_heat_dir = df.set_index('DATE')[dir_cols].T
                fig_hd = px.imshow(df_heat_dir, text_auto=".1f", aspect="auto", color_continuous_scale="Rainbow",
                                   labels={"x": "Bulan", "y": "Arah", "color": "Frekuensi"})
                fig_hd.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_hd, width="stretch")
                
        with col_heat2:
            if speed_cols:
                st.markdown("**Distribusi Kecepatan Angin**")
                df_heat_speed = df.set_index('DATE')[speed_cols].T
                fig_hs = px.imshow(df_heat_speed, text_auto=".1f", aspect="auto", color_continuous_scale="Rainbow",
                                   labels={"x": "Bulan", "y": "Kecepatan (Kts)", "color": "Frekuensi"})
                fig_hs.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_hs, width="stretch")
            
        st.markdown("---")
        col_insight, col_data = st.columns([1, 1])
        
        with col_insight:
            generate_auto_interpretation(df, speed_cols, "Wind Analysis", "Wind")
            st.success("✅ **Operational Note:** " + get_aviation_notes('Wind'))
            
        with col_data:
            st.markdown("### 🗃️ Original Data Table")
            st.dataframe(df, width="stretch", hide_index=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="⬇️ Download CSV", data=csv, 
                               file_name="rekap_wind_2021_2025.csv", mime="text/csv",
                               width="stretch")
    else:
        st.warning("⚠️ Data angin kosong atau gagal diolah.")

def render_home():
    st.title("✈️ Aviation Meteorology Dashboard")
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
        * Interpretasi Meteorologis Berbasis Regulasi (ICAO/WMO)
        * Implikasi Operasional Penerbangan Taktis & Komersial
        """)
    with col2:
        st.info("📊 **Statistik ACS Dashboard**")
        st.write("📅 **Periode Data:** 2021 - 2025")
        st.write("📂 **Total File / Parameter:** 6 Parameter")
        st.write("📈 **Data Integrity:** Original (No Smoothing)")
        st.write("⚙️ **Modul Engine:** Automated Parsing & Robust Data Loader")

# ==========================================
# 5. MAIN ROUTER
# ==========================================
def main():
    try:
        # PENGGANTIAN LOGO TNI AU (SWA BHUWANA PAKSA)
        st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Logo_of_the_Indonesian_Air_Force.svg/800px-Logo_of_the_Indonesian_Air_Force.svg.png", use_container_width=True)
        
        st.sidebar.markdown("## 🧭 Navigasi Menu")
        st.sidebar.caption("Data Rata-Rata: 2021 - 2025")
        
        menu = st.sidebar.radio(
            label="Navigasi Halaman", 
            options=[
                "Home", 
                "Temperature Frequency", 
                "Temperature Mean Max Min", 
                "Relative Humidity", 
                "Visibility", 
                "Cloud Base (HS)", 
                "Wind"
            ],
            label_visibility="collapsed"
        )
        
        st.sidebar.markdown("---")
        st.sidebar.caption("Aviation Meteorology Dashboard © 2026")

        if menu == "Home":
            render_home()
        elif menu == "Temperature Frequency":
            render_generic_page("🌡️ Temperature Frequency", "rekap_temperature_2021_2025.xlsx", "Temperature Freq", 'bar', "Rainbow", "Kategori Suhu (°C)")
        elif menu == "Temperature Mean Max Min":
            render_generic_page("📈 Temperature Mean Max Min", "rekap_temp_max_min_2021_2025.xlsx", "Temperature Mean", 'line', "Rainbow", "Parameter Suhu")
        elif menu == "Relative Humidity":
            render_generic_page("💧 Relative Humidity", "rekap_rh_max_min_2021_2025.xlsx", "Relative Humidity", 'line', "Rainbow", "Waktu Pengamatan (UTC)")
        elif menu == "Visibility":
            render_generic_page("🌫️ Visibility", "rekap_visibility_2021_2025.xlsx", "Visibility", 'bar', "Rainbow", "Kategori Vis (Meter)")
        elif menu == "Cloud Base (HS)":
            render_generic_page("☁️ Cloud Base (Ceiling)", "rekap_hs_2021_2025.xlsx", "Cloud Base", 'bar', "Rainbow", "Kategori HS (Feet)")
        elif menu == "Wind":
            render_wind_page()
            
    except Exception as e:
        st.error(f"🚨 Terjadi kesalahan sistem: {str(e)}")
        st.info("💡 Pastikan format data Excel sesuai dan tidak ada data korup.")

if __name__ == "__main__":
    main()

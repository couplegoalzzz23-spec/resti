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
    """Membaca data secara dinamis, anti-error, dan robust handling."""
    filepath = filename if os.path.exists(filename) else os.path.join("data", filename)
    
    if not os.path.exists(filepath):
        st.error(f"🚨 File tidak ditemukan: `{filename}`. Pastikan nama file sesuai di repositori.")
        return None
        
    try:
        raw_df = pd.read_excel(filepath, header=None)
        
        # Auto-detect Header Row secara dinamis
        header_idx = 0
        for i in range(min(15, len(raw_df))):
            row_vals = [str(x).upper().strip() for x in raw_df.iloc[i].fillna('')]
            if any(c in row_vals for c in ['DATE', 'BULAN', 'MONTH', 'JAN', 'JANUARI', 'JANUARY']):
                if 'JAN' in row_vals or 'JANUARI' in row_vals or 'JANUARY' in row_vals:
                    header_idx = max(0, i - 1)
                else:
                    header_idx = i
                break
        
        df = raw_df.iloc[header_idx+1:].copy()
        df.columns = raw_df.iloc[header_idx].astype(str).str.strip()
        
        # Bersihkan kolom NaN / Unnamed
        df = df.loc[:, df.columns.notna()]
        df = df.loc[:, ~df.columns.str.lower().str.contains('nan|unnamed')]
        
        # Deteksi dan standarisasi kolom tanggal/bulan
        date_col = None
        for col in df.columns:
            if str(col).upper() in ['DATE', 'BULAN', 'MONTH']:
                date_col = col
                break
        if date_col:
            df = df.rename(columns={date_col: 'DATE'})
        else:
            df = df.rename(columns={df.columns[0]: 'DATE'})

        valid_months_map = {
            'JAN': 'Jan', 'FEB': 'Feb', 'MAR': 'Mar', 'APR': 'Apr', 'MAY': 'Mei', 'MEI': 'Mei',
            'JUN': 'Jun', 'JUL': 'Jul', 'AUG': 'Agu', 'AGU': 'Agu', 'SEP': 'Sep', 'OCT': 'Okt',
            'OKT': 'Okt', 'NOV': 'Nov', 'DEC': 'Des', 'DES': 'Des'
        }
        
        df['TEMP_DATE'] = df['DATE'].astype(str).str.upper().str.strip().str[:3]
        df = df[df['TEMP_DATE'].isin(valid_months_map.keys())].copy()
        
        # Mencegah error duplikasi / blank rows
        df = df.drop_duplicates(subset=['TEMP_DATE'], keep='first')
        
        df['DATE'] = df['TEMP_DATE'].map(valid_months_map)
        df = df.drop(columns=['TEMP_DATE'])
        
        # Mengurutkan bulan sesuai kalender (Jan - Des)
        df['DATE_CAT'] = pd.Categorical(df['DATE'], categories=BAKU_MONTHS, ordered=True)
        df = df.sort_values('DATE_CAT').drop(columns=['DATE_CAT']).reset_index(drop=True)
        
        # Casting ke numeric secara aman (kecuali DATE dan indikator string Arah Angin)
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
# 3. AVIATION NOTES MODULE
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

    for col in plot_cols[:3]: 
        max_val = df[col].max()
        if max_val > 0:
            max_month_series = df.loc[df[col] == max_val, 'DATE'].values
            max_month = max_month_series[0] if len(max_month_series) > 0 else "N/A"
            st.write(f"- Peluang frekuensi/intensitas tertinggi untuk kondisi **{col}** terjadi pada bulan **{max_month}** (Nilai tertinggi: {max_val}).")

# ==========================================
# 4. DASHBOARD PAGES & VISUALIZATIONS
# ==========================================
def render_generic_page(title, filename, param_key, chart_type='bar', colorscale="Blues", legend_title="Kategori"):
    st.title(f"{title}")
    st.markdown(f"*{get_aviation_notes(param_key)}*")
    st.markdown("---")
    
    df = load_data(filename)
    if df is not None and not df.empty:
        plot_cols = [c for c in df.columns if str(c).upper() not in ['DATE', 'DIRECTION']]
        
        col_chart, col_metric = st.columns([3, 1])
        
        # Anti-crash visuals: Fallback ke Blues jika warna tidak ditemukan
        safe_colorscale = getattr(px.colors.sequential, colorscale, px.colors.sequential.Blues)
        
        with col_chart:
            st.markdown("### 📈 Interactive Meteogram")
            if chart_type == 'bar':
                # FIX: Mengubah 'stack' menjadi 'group' agar variasi histogram sumbu-y terlihat dan tidak terlihat datar/sama semua
                fig = px.bar(
                    df, x='DATE', y=plot_cols, barmode='group', 
                    color_discrete_sequence=safe_colorscale,
                    labels={"variable": legend_title, "value": "Nilai / Frekuensi", "DATE": "Bulan"}
                )
            else: 
                fig = go.Figure()
                safe_qualitative = getattr(px.colors.qualitative, 'Plotly', ['#003366', '#d62728', '#2ca02c', '#ff7f0e'])
                for idx, col in enumerate(plot_cols):
                    fig.add_trace(go.Scatter(
                        x=df['DATE'], y=df[col], mode='lines+markers', 
                        name=str(col), line=dict(width=3, color=safe_qualitative[idx % len(safe_qualitative)])
                    ))
            
            # Custom Legend 
            fig.update_layout(
                xaxis_title="Bulan", 
                yaxis_title="Frekuensi / Nilai", 
                plot_bgcolor="white", 
                hovermode="x unified",
                legend_title_text=legend_title
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8')
            st.plotly_chart(fig, use_container_width=True)

        with col_metric:
            st.markdown("### 🌡️ Heatmap Profil")
            df_heat = df.set_index('DATE')[plot_cols].T
            fig_heat = px.imshow(
                df_heat, text_auto=".1f", aspect="auto", 
                color_continuous_scale=safe_colorscale,
                labels={"x": "Bulan", "y": legend_title, "color": "Nilai"}
            )
            fig_heat.update_layout(plot_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_heat, use_container_width=True)
            
        st.markdown("---")
        col_insight, col_data = st.columns([1, 1])
        
        with col_insight:
            generate_auto_interpretation(df, plot_cols, title)
            st.success("✅ **Operational Note:** " + get_aviation_notes(param_key))
            
        with col_data:
            st.markdown("### 🗃️ Original Data Table")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="⬇️ Download CSV", data=csv, 
                               file_name=f"{filename.replace('.xlsx', '')}.csv", mime="text/csv",
                               use_container_width=True)
    else:
        st.warning("⚠️ Data kosong atau gagal diolah.")

def render_wind_page():
    st.title("🌬️ Wind Analysis (Arah & Kecepatan)")
    st.markdown(f"*{get_aviation_notes('Wind')}*")
    st.markdown("---")
    
    df = load_data("rekap_wind_2021_2025.xlsx")
    if df is not None and not df.empty:
        # Klasifikasi Kolom Otomatis: Arah (XXX-XXX-XXX format) vs Kecepatan
        dir_cols = [c for c in df.columns if '-' in str(c) and len(str(c).split('-')) == 3]
        speed_cols = [c for c in df.columns if c not in dir_cols and str(c).upper() not in ['DATE', 'CALM', 'DIRECTION']]
        
        st.markdown("### 📈 Unified Interactive Windrose & Speed Distribution")
        
        # FIX WINDROSE: Menggunakan make_subplots untuk menggabungkan Polar Chart (Arah) dan Bar Chart (Kecepatan)
        fig_wind = make_subplots(
            rows=1, cols=2, 
            specs=[[{'type': 'polar'}, {'type': 'xy'}]],
            subplot_titles=("Windrose (Distribusi Arah)", "Distribusi Kecepatan Angin (Bulan)"),
            horizontal_spacing=0.15
        )

        # Plot Arah Angin (Windrose Polar)
        if dir_cols:
            avg_dir = df[dir_cols].mean().reset_index()
            avg_dir.columns = ['Arah', 'Frekuensi']
            
            fig_wind.add_trace(
                go.Barpolar(
                    r=avg_dir['Frekuensi'],
                    theta=avg_dir['Arah'],
                    marker_color=avg_dir['Frekuensi'],
                    marker_colorscale='Turbo', # Gradasi kontras tinggi sesuai permintaan
                    name="Arah Angin (Avg)",
                    showlegend=False
                ),
                row=1, col=1
            )

        # Plot Kecepatan Angin (Bar Chart)
        if speed_cols:
            safe_colorscale = getattr(px.colors.sequential, "Turbo", px.colors.sequential.Viridis)
            # Sample warna berdasar jumlah kategori kecepatan agar kontras
            colors = px.colors.sample_colorscale(safe_colorscale, [i/(len(speed_cols)-1) if len(speed_cols)>1 else 1 for i in range(len(speed_cols))])
            
            for idx, col in enumerate(speed_cols):
                fig_wind.add_trace(
                    go.Bar(
                        x=df['DATE'], 
                        y=df[col], 
                        name=f"{col} Kts",
                        marker_color=colors[idx]
                    ),
                    row=1, col=2
                )
        
        fig_wind.update_layout(
            barmode='group', # Grouped untuk kecepatan agar mudah dibaca frekuensinya
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=True),
                angularaxis=dict(direction="clockwise")
            ),
            legend_title_text="Kategori Kecepatan",
            height=500,
            plot_bgcolor="white"
        )
        fig_wind.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8', row=1, col=2)
        fig_wind.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8', title_text="Frekuensi", row=1, col=2)
        
        st.plotly_chart(fig_wind, use_container_width=True)

        # Heatmap Terpisah untuk Wind
        st.markdown("### 🌡️ Heatmap Profil Angin")
        col_heat1, col_heat2 = st.columns(2)
        
        with col_heat1:
            if dir_cols:
                st.markdown("**Distribusi Arah Angin**")
                df_heat_dir = df.set_index('DATE')[dir_cols].T
                fig_hd = px.imshow(df_heat_dir, text_auto=".1f", aspect="auto", color_continuous_scale="Turbo",
                                   labels={"x": "Bulan", "y": "Arah", "color": "Frekuensi"})
                fig_hd.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_hd, use_container_width=True)
                
        with col_heat2:
            if speed_cols:
                st.markdown("**Distribusi Kecepatan Angin**")
                df_heat_speed = df.set_index('DATE')[speed_cols].T
                fig_hs = px.imshow(df_heat_speed, text_auto=".1f", aspect="auto", color_continuous_scale="Turbo",
                                   labels={"x": "Bulan", "y": "Kecepatan (Kts)", "color": "Frekuensi"})
                fig_hs.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_hs, use_container_width=True)
            
        st.markdown("---")
        col_insight, col_data = st.columns([1, 1])
        with col_insight:
            st.success("✅ **Operational Note:** " + get_aviation_notes('Wind'))
        with col_data:
            st.markdown("### 🗃️ Original Data Table")
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="⬇️ Download CSV", data=csv, 
                               file_name="rekap_wind_2021_2025.csv", mime="text/csv",
                               use_container_width=True)
    else:
        st.warning("⚠️ Data angin kosong atau gagal diolah.")

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
        st.write("⚙️ **Modul Engine:** Automated Parsing & Robust Data Loader")

# ==========================================
# 5. MAIN ROUTER
# ==========================================
def main():
   
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
    st.sidebar.caption("Aviation Weather Statistics © 2026")

    # Routing berdasarkan menu yang dipilih
    if menu == "Home":
        render_home()
    elif menu == "Temperature Frequency":
        render_generic_page("🌡️ Temperature Frequency", "rekap_temperature_2021_2025.xlsx", "Temperature Freq", 'bar', "Reds", "Kategori Suhu (°C)")
    elif menu == "Temperature Mean Max Min":
        render_generic_page("📈 Temperature Mean Max Min", "rekap_temp_max_min_2021_2025.xlsx", "Temperature Mean", 'line', "Reds", "Parameter Suhu")
    elif menu == "Relative Humidity":
        render_generic_page("💧 Relative Humidity", "rekap_rh_max_min_2021_2025.xlsx", "Relative Humidity", 'line', "Teal", "Waktu Pengamatan (UTC)")
    elif menu == "Visibility":
        render_generic_page("🌫️ Visibility", "rekap_visibility_2021_2025.xlsx", "Visibility", 'bar', "Greens", "Jarak Pandang (Meter)")
    elif menu == "Cloud Base (HS)":
        render_generic_page("☁️ Cloud Base (Ceiling)", "rekap_hs_2021_2025.xlsx", "Cloud Base", 'bar', "Blues", "Tinggi Awan (Feet)")
    elif menu == "Wind":
        render_wind_page()

if __name__ == "__main__":
    main()

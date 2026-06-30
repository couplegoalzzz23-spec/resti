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
    .sidebar .sidebar-content { background-color: #FFFFFF; box-shadow: 2px 0 5px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True)

BAKU_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

# ==========================================
# 2. ROBUST DATA LOADER MODULE
# ==========================================
@st.cache_data(show_spinner=False)
def load_data(filename):
    filepath = filename if os.path.exists(filename) else os.path.join("data", filename)
    if not os.path.exists(filepath):
        st.error(f"🚨 File tidak ditemukan: `{filename}`. Pastikan file ada di repositori GitHub.")
        return None
        
    try:
        raw_df = pd.read_excel(filepath, header=None)
        
        # Auto-detect Header Row
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
        
        # Bersihkan kolom kotor
        df = df.loc[:, df.columns.notna()]
        df = df.loc[:, ~df.columns.str.lower().str.contains('nan|unnamed')]
        
        # Rename kolom tanggal
        date_col = next((col for col in df.columns if str(col).upper() in ['DATE', 'BULAN', 'MONTH']), df.columns[0])
        df = df.rename(columns={date_col: 'DATE'})

        # Filter hanya data bulanan yang valid
        valid_months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'MEI', 'JUN', 'JUL', 'AUG', 'AGU', 'SEP', 'OCT', 'OKT', 'NOV', 'DEC', 'DES']
        df['TEMP_DATE'] = df['DATE'].astype(str).str.upper().str.strip().str[:3]
        df = df[df['TEMP_DATE'].isin(valid_months)].copy()
        df = df.drop(columns=['TEMP_DATE'])
        
        # Urutkan bulan baku
        if len(df) >= 12:
            df['DATE'] = BAKU_MONTHS[:len(df)]
        
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"🚨 Gagal memproses file {filename}: {e}")
        return None

# ==========================================
# 3. PAGE RENDERERS
# ==========================================
def render_wind_page():
    st.title("🌬️ Wind Analysis (Angin Permukaan)")
    st.markdown("*Distribusi arah dan kecepatan angin menentukan orientasi operasional runway dan potensi hazard seperti crosswind.*")
    st.markdown("---")
    
    df = load_data("rekap_wind_2021_2025.xlsx")
    if df is None: return

    # Konversi tipe data numerik
    for col in df.columns:
        if col not in ['DATE', 'DIRECTION']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Memisahkan kategori kolom berdasarkan format nama di Excel
    direction_cols = [c for c in df.columns if '-' in c and len(c.split('-')) == 3] # ex: 35 - 36 - 01
    speed_cols = [c for c in df.columns if ('-' in c and len(c.split('-')) == 2) or '>' in c] # ex: 1 - 5, > 45

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🧭 Rata-rata Arah Angin (Wind Rose)")
        # Plot Wind Rose secara rata-rata tahunan
        dir_means = df[direction_cols].mean()
        fig_polar = px.bar_polar(
            r=dir_means.values, 
            theta=dir_means.index, 
            color_discrete_sequence=px.colors.sequential.Blues_r,
            template="plotly_white",
            labels={"r": "Frekuensi (%)", "theta": "Sektor Arah"}
        )
        st.plotly_chart(fig_polar, use_container_width=True)

    with col2:
        st.subheader("💨 Distribusi Kecepatan Angin per Bulan")
        fig_speed = px.bar(
            df, x='DATE', y=speed_cols, barmode='stack',
            color_discrete_sequence=px.colors.sequential.Purples_r
        )
        fig_speed.update_layout(
            xaxis_title="Bulan", 
            yaxis_title="Frekuensi (%)",
            legend_title_text="Kategori Kecepatan (Knots)",
            hovermode="x unified"
        )
        st.plotly_chart(fig_speed, use_container_width=True)

    st.markdown("### 🗃️ Tabel Data Original")
    st.dataframe(df, use_container_width=True, hide_index=True)

def render_generic_page(title, filename, legend_title, chart_type='bar', colorscale="Blues"):
    st.title(f"{title}")
    st.markdown("---")
    
    df = load_data(filename)
    if df is not None:
        # Konversi ke numerik
        plot_cols = [c for c in df.columns if c != 'DATE']
        for col in plot_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        col_chart, col_metric = st.columns([2.5, 1.5])
        
        # Pengambilan warna Plotly dengan aman (Anti-Crash)
        safe_colorscale = getattr(px.colors.sequential, colorscale, px.colors.sequential.Blues)
        
        with col_chart:
            st.markdown("### 📈 Interactive Meteogram")
            if chart_type == 'bar':
                fig = px.bar(df, x='DATE', y=plot_cols, barmode='stack', color_discrete_sequence=safe_colorscale)
            else:
                fig = go.Figure()
                colors = ['#003366', '#d62728', '#2ca02c', '#ff7f0e']
                for idx, col in enumerate(plot_cols):
                    fig.add_trace(go.Scatter(x=df['DATE'], y=df[col], mode='lines+markers', 
                                             name=col, line=dict(width=3, color=colors[idx % len(colors)])))
            
            # MENGGANTI LABEL "PARAMETER" MENJADI SESUAI KONTEKS
            fig.update_layout(
                xaxis_title="Bulan", 
                yaxis_title="Nilai / Frekuensi", 
                legend_title_text=legend_title, # <--- Label Legenda di-Set Disini
                hovermode="x unified",
                plot_bgcolor="white"
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E8E8E8')
            st.plotly_chart(fig, use_container_width=True)

        with col_metric:
            st.markdown("### 🌡️ Heatmap Profil")
            df_heat = df.set_index('DATE')[plot_cols].T
            fig_heat = px.imshow(df_heat, text_auto=".1f", aspect="auto", color_continuous_scale=safe_colorscale)
            fig_heat.update_layout(plot_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_heat, use_container_width=True)
            
        st.markdown("### 🗃️ Original Data Table")
        st.dataframe(df, use_container_width=True, hide_index=True)

# ==========================================
# 4. MAIN ROUTER
# ==========================================
def main():
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_BMKG.png", width=80)
    st.sidebar.markdown("## 🧭 Navigasi Menu")
    
    menu = st.sidebar.radio("", [
        "Home", 
        "Temperature Frequency", 
        "Temperature Mean Max Min", 
        "Relative Humidity", 
        "Visibility", 
        "Cloud Base (HS)", 
        "Wind"
    ])
    
    if menu == "Home":
        st.title("✈️ Aviation Climatology Dashboard (ACS)")
        st.info("Pilih parameter di sidebar sebelah kiri untuk melihat analisis klimatologi operasional bandara (Periode 2021-2025).")
    
    elif menu == "Temperature Frequency":
        render_generic_page("🌡️ Temperature Frequency", "rekap_temperature_2021_2025.xlsx", "Kategori Suhu (°C)", 'bar', "Reds")
    elif menu == "Temperature Mean Max Min":
        render_generic_page("📈 Temperature Mean, Max, Min", "rekap_temp_max_min_2021_2025.xlsx", "Parameter Suhu (°C)", 'line', "Reds")
    elif menu == "Relative Humidity":
        render_generic_page("💧 Relative Humidity", "rekap_rh_max_min_2021_2025.xlsx", "Parameter RH (%)", 'line', "Teal")
    elif menu == "Visibility":
        render_generic_page("🌫️ Visibility (Jarak Pandang)", "rekap_visibility_2021_2025.xlsx", "Kategori Visibilitas (m)", 'bar', "Greens")
    elif menu == "Cloud Base (HS)":
        render_generic_page("☁️ Cloud Base (Ceiling)", "rekap_hs_2021_2025.xlsx", "Kategori Awan (ft)", 'bar', "Blues")
    elif menu == "Wind":
        render_wind_page()

if __name__ == "__main__":
    main()

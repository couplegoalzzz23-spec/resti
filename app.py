import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="ACS Dashboard", layout="wide")

# ==========================================
# 2. CORE DATA ENGINE
# ==========================================
@st.cache_data(show_spinner=False)
def load_and_clean_data(filename):
    filepath = filename if os.path.exists(filename) else os.path.join("data", filename)
    if not os.path.exists(filepath): return None
    
    # Deteksi Header yang dinamis
    raw_df = pd.read_excel(filepath, header=None)
    header_row = 0
    for i in range(min(10, len(raw_df))):
        if 'DATE' in raw_df.iloc[i].astype(str).str.upper().values:
            header_row = i
            break
            
    df = raw_df.iloc[header_row+1:].copy()
    df.columns = raw_df.iloc[header_row].astype(str).str.strip()
    df = df.loc[:, df.columns.notna()]
    df = df.rename(columns={df.columns[0]: 'DATE'})
    
    # Filter hanya bulan
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    df['DATE'] = df['DATE'].astype(str).str.upper().str[:3]
    df = df[df['DATE'].isin(months)].reset_index(drop=True)
    
    # Numeric cleanup
    for col in df.columns:
        if col != 'DATE':
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# ==========================================
# 3. PAGES
# ==========================================
def render_wind_page():
    st.title("🌬️ Wind Analysis (Wind Rose Distribution)")
    df = load_and_clean_data("rekap_wind_2021_2025.xlsx")
    if df is None: return

    # Mengambil kolom kategori kecepatan angin
    wind_cols = [c for c in df.columns if c not in ['DATE', 'DIRECTION', 'CALM']]
    
    # Visualisasi Wind Rose Sederhana (Polar Bar Chart)
    fig = go.Figure()
    for col in wind_cols:
        fig.add_trace(go.Barpolar(
            r=df[col],
            theta=df['DATE'], # Sebagai representasi bulan
            name=f"Speed: {col} knots"
        ))
    
    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True, title="Distribusi Frekuensi Angin per Bulan")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True)

def render_generic_page(title, filename, unit="Unit"):
    st.title(title)
    df = load_and_clean_data(filename)
    if df is None: return
    
    cols = [c for c in df.columns if c != 'DATE']
    
    # Bar Chart Stacked
    fig = px.bar(df, x='DATE', y=cols, title=f"Distribusi {title}", barmode='stack', labels={'value': unit})
    st.plotly_chart(fig, use_container_width=True)
    
    # Heatmap
    df_heat = df.set_index('DATE')
    st.subheader("Heatmap Intensitas")
    st.plotly_chart(px.imshow(df_heat, text_auto=".1f", color_continuous_scale="Blues"), use_container_width=True)

# ==========================================
# 4. MAIN NAVIGATION
# ==========================================
def main():
    st.sidebar.title("Aviation Climatology")
    page = st.sidebar.radio("Pilih Analisis:", 
        ["Home", "Wind Analysis", "Visibility", "Cloud Base", "Temperature", "Humidity"])

    if page == "Home":
        st.title("Aviation Climatology Summary (ACS)")
        st.markdown("""
        Dashboard ini menyajikan data klimatologi bandara 2021-2025.
        Tujuan: Membantu operasional penerbangan dalam menentukan prosedur keselamatan (LVP), 
        pemilihan runway, dan manajemen beban muatan.
        """)
    elif page == "Wind Analysis": render_wind_page()
    elif page == "Visibility": render_generic_page("Visibility (Jarak Pandang)", "rekap_visibility_2021_2025.xlsx", "Frekuensi (%)")
    elif page == "Cloud Base": render_generic_page("Cloud Base (Ceiling)", "rekap_hs_2021_2025.xlsx", "Frekuensi (%)")
    elif page == "Temperature": render_generic_page("Temperature Frequency", "rekap_temperature_2021_2025.xlsx", "Frekuensi (%)")
    elif page == "Humidity": render_generic_page("Relative Humidity", "rekap_rh_max_min_2021_2025.xlsx", "% RH")

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import plotly.express as px
import folium
import json
from streamlit_folium import folium_static

st.title("📊 Peta & Statistik Harga Komoditas")

# ==== Sidebar Upload ====
st.sidebar.header("📁 Upload Data")
uploaded_file = st.sidebar.file_uploader("Unggah File Excel", type=["xlsx"])

# Load data
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ File berhasil diunggah!")
else:
    df = pd.read_excel("Data Harga Komoditas.xlsx")
    st.info("📌 Menggunakan data default karena tidak ada file diunggah.")

# Load GeoJSON (gunakan default)
with open("prov 38.json", "r") as f:
    geojson = json.load(f)

# Dropdown bahan pokok
bahan_list = df["Nama Variant"].unique()
selected_bahan = st.selectbox("Pilih Bahan Pokok", bahan_list)

# Dropdown agregasi
agregasi_opsi = {
    "Harga Terendah": "min",
    "Harga Tertinggi": "max"
}
selected_agregasi_label = st.selectbox("Pilih Metode Agregasi Harga", list(agregasi_opsi.keys()))
agregasi_func = agregasi_opsi[selected_agregasi_label]

# Kolom tanggal terakhir = kolom paling kanan
tanggal_terakhir = df.columns[-1]

# Filter berdasarkan bahan pokok
filtered_df = df[df["Nama Variant"] == selected_bahan]

# Ambil kolom harga dari kolom tanggal terakhir dan beri nama 'harga'
filtered_df = filtered_df[["Provinsi", "Nama Variant", tanggal_terakhir]].copy()
filtered_df.rename(columns={tanggal_terakhir: "harga"}, inplace=True)
filtered_df["Provinsi"] = filtered_df["Provinsi"].str.upper().str.strip()

# Agregasi per provinsi
agg_df = filtered_df.groupby("Provinsi").agg({"harga": agregasi_func}).reset_index()

# Ubah nama provinsi di GeoJSON agar cocok
for feature in geojson["features"]:
    feature["properties"]["PROVINSI"] = feature["properties"]["PROVINSI"].upper()

# Gabungkan harga ke GeoJSON
harga_dict = dict(zip(agg_df["Provinsi"], agg_df["harga"]))
for feature in geojson["features"]:
    prov_name = feature["properties"]["PROVINSI"]
    feature["properties"]["harga"] = harga_dict.get(prov_name, "Data tidak tersedia")

# Buat peta
m = folium.Map(location=[-2.5, 118], zoom_start=5, tiles="CartoDB positron")

# Tambahkan Choropleth
choropleth = folium.Choropleth(
    geo_data=geojson,
    data=agg_df,
    columns=["Provinsi", "harga"],
    key_on="feature.properties.PROVINSI",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name=f"Harga {selected_bahan} ({selected_agregasi_label})",
    highlight=True,
).add_to(m)

# Tambahkan popups interaktif
for feature in geojson["features"]:
    prov_name = feature["properties"]["PROVINSI"]
    harga = feature["properties"]["harga"]
    popup_html = f"<b>{prov_name}</b><br>Harga: Rp {harga:,.0f}" if isinstance(harga, (int, float)) else f"<b>{prov_name}</b><br>{harga}"
    folium.GeoJson(
        data=feature,
        style_function=lambda x: {"fillColor": "#transparent", "color": "#000000", "weight": 0.3, "fillOpacity": 0},
        highlight_function=lambda x: {"weight": 3, "color": "blue"},
        tooltip=folium.Tooltip(popup_html, sticky=True)
    ).add_to(m)

# Tampilkan peta
st.subheader(f"Peta Harga per Provinsi - {tanggal_terakhir}")
folium_static(m)

# Grafik Perbandingan Harga (Bar Chart)
bar_fig = px.bar(
    agg_df,
    x="Provinsi",
    y="harga",
    title=f"Perbandingan Harga {selected_bahan} per Provinsi ({selected_agregasi_label}) - {tanggal_terakhir}",
    labels={"harga": "Harga", "Provinsi": "Provinsi"},
    color="harga",
    color_continuous_scale="YlOrRd"
)
st.plotly_chart(bar_fig, use_container_width=True)

# Pastikan kolom tanggal adalah string dan mengandung '/'
date_columns = [col for col in df.columns if isinstance(col, str) and '/' in col]

# Filter data berdasarkan bahan pokok yang dipilih
filtered_df = df[df["Nama Variant"] == selected_bahan]

# Menghitung rata-rata harga per tanggal untuk bahan pokok yang dipilih
df_avg = filtered_df[["Nama Variant"] + date_columns]
df_avg = df_avg.drop(columns=["Nama Variant"])  # Hapus kolom Nama Variant setelah filter
df_avg = df_avg.mean()  # Hitung rata-rata harga untuk setiap tanggal

# Ubah hasil rata-rata menjadi DataFrame dengan index sebagai tanggal
df_avg = pd.DataFrame(df_avg).reset_index()
df_avg.columns = ["Tanggal", "Harga Rata-rata Nasional"]

# Ubah kolom tanggal menjadi datetime
df_avg["Tanggal"] = pd.to_datetime(df_avg["Tanggal"], format="%d/%m/%y")

# Plot perkembangan harga rata-rata nasional untuk bahan pokok yang dipilih
fig_line = px.line(
    df_avg,
    x="Tanggal",
    y="Harga Rata-rata Nasional",
    title=f"Perkembangan Harga Nasional {selected_bahan} (Rata-rata Harga per Tanggal)",
    labels={"Harga Rata-rata Nasional": "Harga", "Tanggal": "Tanggal"},
    line_shape="linear"
)
st.plotly_chart(fig_line, use_container_width=True)

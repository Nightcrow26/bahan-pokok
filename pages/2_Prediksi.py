import streamlit as st
import pandas as pd
import joblib
import gdown
import datetime
import plotly.graph_objects as go
import os
from io import BytesIO

st.title("🔮 Prediksi Harga Komoditas")

# === Unduh model dan encoder jika belum tersedia ===
url_model = 'https://drive.google.com/uc?id=1OKajzFzbAOuwliw8LwD8aF9_dscKhXam'
output_model = 'model_rf_harga.pkl'

url_encoder = 'https://drive.google.com/uc?id=1vmcx3F1c95ufQnQLaaWPmSzDsms3VnCr'
output_encoder = 'label_encoder_dict.pkl'

if not os.path.exists(output_model):
    gdown.download(url_model, output_model, quiet=False)
if not os.path.exists(output_encoder):
    gdown.download(url_encoder, output_encoder, quiet=False)

# === Load model dan encoder ===
model = joblib.load(output_model)
le_dict = joblib.load(output_encoder)

# === Dropdown user input ===
provinsi = st.selectbox("Pilih Provinsi", le_dict["Provinsi"].classes_)
kab_kota = st.selectbox("Pilih Kabupaten/Kota", le_dict["Kabupaten Kota"].classes_)
nama_pasar = st.selectbox("Pilih Nama Pasar", le_dict["Nama Pasar"].classes_)
nama_variant = st.selectbox("Pilih Komoditas", le_dict["Nama Variant"].classes_)
tanggal = st.date_input("Tanggal", value=datetime.date.today())

# === Pilih jangka waktu prediksi ===
pred_range = st.radio("Jangka Waktu Prediksi", ["Hari Ini & Besok", "1 Minggu", "1 Bulan"])

if st.button("Prediksi"):
    def encode_input(tgl):
        return {
            "Provinsi": le_dict["Provinsi"].transform([provinsi])[0],
            "Kabupaten Kota": le_dict["Kabupaten Kota"].transform([kab_kota])[0],
            "Nama Pasar": le_dict["Nama Pasar"].transform([nama_pasar])[0],
            "Nama Variant": le_dict["Nama Variant"].transform([nama_variant])[0],
            "day": tgl.day,
            "month": tgl.month,
            "dayofweek": tgl.weekday()
        }

    if pred_range == "Hari Ini & Besok":
        input_today = encode_input(tanggal)
        pred_today = model.predict(pd.DataFrame([input_today]))[0]

        besok = tanggal + datetime.timedelta(days=1)
        input_besok = encode_input(besok)
        pred_tomorrow = model.predict(pd.DataFrame([input_besok]))[0]

        st.markdown(f"📅 **Harga Hari Ini ({tanggal}):** Rp {pred_today:,.2f}")
        st.markdown(f"📅 **Harga Besok ({besok}):** Rp {pred_tomorrow:,.2f}")

        if pred_tomorrow > pred_today:
            st.markdown("### 🔺 Harga Diprediksi **Naik**")
        elif pred_tomorrow < pred_today:
            st.markdown("### 🔻 Harga Diprediksi **Turun**")
        else:
            st.markdown("### ➡️ Harga Diprediksi **Stabil**")

        # Visualisasi
        fig = go.Figure([go.Bar(x=["Hari Ini", "Besok"], y=[pred_today, pred_tomorrow], marker_color=["blue", "red"])])
        fig.update_layout(title="Perbandingan Harga", xaxis_title="Hari", yaxis_title="Harga", yaxis_tickprefix="Rp ")
        st.plotly_chart(fig, use_container_width=True)

    else:
        # Prediksi 7 atau 30 hari ke depan
        n_days = 7 if pred_range == "1 Minggu" else 30
        future_dates = [tanggal + datetime.timedelta(days=i) for i in range(n_days)]
        input_data = [encode_input(tgl) for tgl in future_dates]
        input_df = pd.DataFrame(input_data)
        pred_prices = model.predict(input_df)

        pred_df = pd.DataFrame({
            "Tanggal": future_dates,
            "Harga": pred_prices
        })

        # Visualisasi line chart
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=pred_df["Tanggal"], y=pred_df["Harga"], mode="lines+markers", line=dict(color="green")))
        fig.update_layout(title=f"Prediksi Harga untuk {n_days} Hari ke Depan", xaxis_title="Tanggal",
                          yaxis_title="Harga", yaxis_tickprefix="Rp ")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(pred_df.set_index("Tanggal").style.format({"Harga": "Rp {:,.2f}"}))

        # === Download Section ===
        st.markdown("### 📥 Unduh Hasil Prediksi")

        # Convert to CSV
        csv = pred_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📄 Download CSV",
            data=csv,
            file_name=f'prediksi_{nama_variant}_{n_days}_hari.csv',
            mime='text/csv'
        )

        # Excel Download
        excel_buffer = BytesIO()
        pred_df.to_excel(excel_buffer, index=False, sheet_name="Prediksi")
        excel_buffer.seek(0)

        st.download_button(
            label="📊 Download Excel",
            data=excel_buffer,
            file_name=f'prediksi_{nama_variant}_{n_days}_hari.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


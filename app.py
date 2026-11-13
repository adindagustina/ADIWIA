
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from io import BytesIO
from google import genai
from dotenv import load_dotenv

# =====================================================
# 1. KONFIGURASI APLIKASI
# =====================================================

st.set_page_config(
    page_title="ADIWIA - Asisten Digital Audit",
    page_icon="📊",
    layout="wide"
)

load_dotenv()

MODEL_NAME = "gemini-3.8-flash"

API_KEY = os.getenv("GEMINI_API_KEY")

try:
    if not API_KEY:
        API_KEY = st.secrets.get("GEMINI_API_KEY")
except Exception:
    API_KEY = None

client = None

if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception:
        client = None


# =====================================================
# 2. FUNGSI GEMINI
# =====================================================

def ask_gemini(prompt, retries=3):

    if client is None:
        return "Gemini API belum dikonfigurasi. Periksa Streamlit Secrets."

    for attempt in range(retries):

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            return response.text or "Gemini tidak memberikan jawaban."

        except Exception as e:

            error_message = str(e)

            temporary_error = any(
                code in error_message
                for code in ["503", "429", "500", "504", "UNAVAILABLE"]
            )

            if temporary_error and attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue

            if "503" in error_message or "UNAVAILABLE" in error_message:
                return (
                    "Layanan Gemini sedang mengalami kepadatan pengguna. "
                    "Silakan coba kembali beberapa saat lagi."
                )

            if "429" in error_message:
                return (
                    "Batas penggunaan Gemini API sedang tercapai. "
                    "Silakan tunggu sebelum mencoba kembali."
                )

            return f"Terjadi kesalahan Gemini API: {error_message}"

    return "Gemini belum dapat memberikan respons."


# =====================================================
# 3. JUDUL APLIKASI
# =====================================================

st.title("📊 ADIWIA")

st.subheader("Asisten Digital Audit Widianti & Adinda")

st.write(
    "Asisten digital berbasis Artificial Intelligence "
    "untuk membantu pemeriksaan, analisis, dan evaluasi data keuangan."
)

st.divider()


# =====================================================
# 4. UPLOAD DATA AUDIT
# =====================================================

st.header("📂 1. Upload Data Audit")

uploaded_file = st.file_uploader(
    "Unggah data keuangan dalam format Excel",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Silakan unggah file Excel untuk memulai pemeriksaan.")
    st.stop()

try:
    df = pd.read_excel(uploaded_file)

    df.columns = [str(col).strip() for col in df.columns]

    if df.empty:
        st.warning("File Excel tidak memiliki data transaksi.")
        st.stop()

    st.success("Data berhasil diunggah!")

except Exception as e:
    st.error(f"Gagal membaca file Excel: {e}")
    st.stop()


# =====================================================
# 5. INFORMASI DATA
# =====================================================

st.header("📊 2. Informasi Data")

total_transaksi = len(df)
total_kolom = len(df.columns)
total_kosong = int(df.isna().sum().sum())

col1, col2, col3 = st.columns(3)

col1.metric("Jumlah Transaksi", total_transaksi)
col2.metric("Jumlah Kolom", total_kolom)
col3.metric("Data Kosong", total_kosong)

st.subheader("Pratinjau Data")

st.dataframe(
    df.head(20),
    use_container_width=True
)


# =====================================================
# 6. PEMERIKSAAN DATA AUDIT
# =====================================================

st.header("🔍 3. Pemeriksaan Data Audit")

findings = []

# -----------------------------------------------------
# A. PEMERIKSAAN DATA KOSONG
# -----------------------------------------------------

st.subheader("Pemeriksaan Kelengkapan Data")

missing_summary = df.isna().sum()

missing_data = []

for column, count in missing_summary.items():

    if count > 0:

        missing_data.append({
            "Kolom": column,
            "Jumlah Data Kosong": int(count)
        })

        findings.append({
            "Jenis Temuan": "Data Kosong",
            "Keterangan": (
                f"Kolom {column} memiliki {int(count)} data kosong."
            )
        })

if missing_data:

    st.warning("Ditemukan data yang belum lengkap.")

    st.dataframe(
        pd.DataFrame(missing_data),
        use_container_width=True
    )

else:
    st.success("Tidak ditemukan data kosong.")


# -----------------------------------------------------
# B. PEMERIKSAAN DATA DUPLIKAT
# -----------------------------------------------------

st.subheader("Pemeriksaan Data Duplikat")

duplicate_rows = df[df.duplicated(keep=False)]

duplicate_count = int(df.duplicated().sum())

if duplicate_count > 0:

    st.warning(
        f"Ditemukan {duplicate_count} baris data yang terduplikasi."
    )

    findings.append({
        "Jenis Temuan": "Data Duplikat",
        "Keterangan": (
            f"Ditemukan {duplicate_count} baris data duplikat."
        )
    })

    with st.expander("Lihat Detail Data Duplikat"):

        st.dataframe(
            duplicate_rows,
            use_container_width=True
        )

else:
    st.success("Tidak ditemukan baris data duplikat.")


# -----------------------------------------------------
# C. PEMERIKSAAN NOMINAL TRANSAKSI
# -----------------------------------------------------

st.subheader("Pemeriksaan Nominal Transaksi")

numeric_columns = df.select_dtypes(
    include="number"
).columns.tolist()

amount_candidates = [
    col for col in numeric_columns
    if str(col).strip().lower().replace(" ", "_")
    in [
        "amount",
        "amount_usd",
        "nominal",
        "jumlah",
        "nilai",
        "actual",
        "realisasi"
    ]
]

if amount_candidates:

    amount_column = st.selectbox(
        "Pilih kolom nominal yang akan diperiksa",
        amount_candidates
    )

    values = df[amount_column].dropna()

    if len(values) >= 4:

        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1

        if iqr > 0:

            lower_limit = q1 - (1.5 * iqr)
            upper_limit = q3 + (1.5 * iqr)

            outlier_mask = (
                (df[amount_column] < lower_limit) |
                (df[amount_column] > upper_limit)
            )

            outlier_data = df[outlier_mask]

            if not outlier_data.empty:

                st.warning(
                    f"Ditemukan {len(outlier_data)} transaksi "
                    "dengan nilai yang tidak biasa."
                )

                findings.append({
                    "Jenis Temuan": "Nominal Tidak Biasa",
                    "Keterangan": (
                        f"Ditemukan {len(outlier_data)} transaksi "
                        f"pada kolom {amount_column} di luar batas IQR."
                    )
                })

                with st.expander("Lihat Detail Nominal Tidak Biasa"):

                    st.dataframe(
                        outlier_data,
                        use_container_width=True
                    )

            else:
                st.success(
                    "Tidak ditemukan nominal di luar batas IQR."
                )

        else:
            st.info(
                "Nilai transaksi relatif sama sehingga "
                "pemeriksaan IQR dilewati."
            )

    else:
        st.info("Data belum cukup untuk pemeriksaan IQR.")

else:
    st.info(
        "Kolom nominal belum ditemukan. "
        "Pastikan terdapat kolom angka yang sesuai."
    )


# -----------------------------------------------------
# D. PEMERIKSAAN DEBIT DAN KREDIT
# -----------------------------------------------------

st.subheader("Pemeriksaan Debit dan Kredit")

def normalize_column(name):
    return str(name).strip().lower().replace(" ", "_")

column_lookup = {
    normalize_column(col): col
    for col in df.columns
}

debit_aliases = [
    "debit",
    "debet",
    "debit_amount",
    "jumlah_debit",
    "debit_rp"
]

credit_aliases = [
    "credit",
    "kredit",
    "credit_amount",
    "jumlah_kredit",
    "kredit_rp"
]

debit_column = next(
    (
        column_lookup[x]
        for x in debit_aliases
        if x in column_lookup
    ),
    None
)

credit_column = next(
    (
        column_lookup[x]
        for x in credit_aliases
        if x in column_lookup
    ),
    None
)

if debit_column and credit_column:

    debit_total = pd.to_numeric(
        df[debit_column],
        errors="coerce"
    ).sum()

    credit_total = pd.to_numeric(
        df[credit_column],
        errors="coerce"
    ).sum()

    col1, col2 = st.columns(2)

    col1.metric("Total Debit", f"{debit_total:,.2f}")
    col2.metric("Total Kredit", f"{credit_total:,.2f}")

    difference = debit_total - credit_total

    if abs(difference) < 0.01:

        st.success("Total debit dan kredit seimbang.")

    else:

        st.error(
            f"Debit dan kredit tidak seimbang. "
            f"Selisih: {difference:,.2f}"
        )

        findings.append({
            "Jenis Temuan": "Debit dan Kredit Tidak Seimbang",
            "Keterangan": (
                f"Selisih total debit dan kredit sebesar "
                f"{difference:,.2f}."
            )
        })

else:

    st.info(
        "Pemeriksaan debit dan kredit dilewati karena "
        "kolom debit atau kredit tidak tersedia."
    )


# =====================================================
# 7. ANALISIS ANGGARAN DAN REALISASI
# =====================================================

st.header("💰 4. Analisis Anggaran dan Realisasi")

budget_column = column_lookup.get("budget")
actual_column = column_lookup.get("actual")
category_column = column_lookup.get("category")

if budget_column and actual_column:

    budget_values = pd.to_numeric(
        df[budget_column],
        errors="coerce"
    )

    actual_values = pd.to_numeric(
        df[actual_column],
        errors="coerce"
    )

    df["Variance"] = budget_values - actual_values

    df["Variance %"] = (
        df["Variance"] /
        budget_values.replace(0, float("nan"))
    ) * 100

    total_budget = budget_values.sum()
    total_actual = actual_values.sum()

    variance = total_budget - total_actual

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Anggaran", f"{total_budget:,.2f}")
    col2.metric("Total Realisasi", f"{total_actual:,.2f}")
    col3.metric("Selisih", f"{variance:,.2f}")

    if category_column:

        st.subheader("Grafik Anggaran dan Realisasi")

        chart_data = df.groupby(
            category_column
        )[[budget_column, actual_column]].sum().reset_index()

        chart_data = chart_data.melt(
            id_vars=category_column,
            var_name="Jenis",
            value_name="Jumlah"
        )

        fig = px.bar(
            chart_data,
            x=category_column,
            y="Jumlah",
            color="Jenis",
            barmode="group",
            title="Perbandingan Anggaran dan Realisasi"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    overspending = df[
        actual_values > budget_values
    ]

    if not overspending.empty:

        st.warning(
            f"Ditemukan {len(overspending)} data "
            "dengan realisasi melebihi anggaran."
        )

        findings.append({
            "Jenis Temuan": "Realisasi Melebihi Anggaran",
            "Keterangan": (
                f"Ditemukan {len(overspending)} data "
                "dengan realisasi lebih besar daripada anggaran."
            )
        })

        with st.expander("Lihat Detail Anggaran dan Realisasi"):

            st.dataframe(
                overspending,
                use_container_width=True
            )

    else:
        st.success(
            "Tidak ditemukan realisasi yang melebihi anggaran."
        )

else:

    st.info(
        "Analisis anggaran dan realisasi memerlukan "
        "kolom bernama Budget dan Actual."
    )


# =====================================================
# 8. RINGKASAN TEMUAN AUDIT
# =====================================================

st.header("🚨 5. Ringkasan Temuan Audit")

if findings:

    findings_df = pd.DataFrame(findings)

    st.warning(
        f"ADIWIA menemukan {len(findings)} indikasi "
        "yang perlu diperiksa lebih lanjut."
    )

    st.dataframe(
        findings_df,
        use_container_width=True
    )

else:

    findings_df = pd.DataFrame(
        columns=["Jenis Temuan", "Keterangan"]
    )

    st.success(
        "Tidak ditemukan indikasi berdasarkan "
        "pemeriksaan otomatis yang dilakukan."
    )

st.caption(
    "Catatan: Temuan otomatis merupakan indikator awal "
    "dan tetap memerlukan verifikasi auditor."
)


# =====================================================
# 9. AI AUDIT ANALYSIS
# =====================================================

st.header("🤖 6. AI Audit Analysis")

if client is None:

    st.warning(
        "Fitur AI belum aktif. Tambahkan Gemini API Key "
        "pada Streamlit Secrets untuk menggunakannya."
    )

else:

    st.info(
        "AI membantu memberikan analisis berdasarkan "
        "data dan hasil pemeriksaan otomatis."
    )

    if st.button("Mulai Analisis AI"):

        with st.spinner("ADIWIA sedang menganalisis data..."):

            summary = f"""
            Jumlah transaksi: {len(df)}
            Jumlah kolom: {len(df.columns)}
            Jumlah data kosong: {total_kosong}
            Jumlah duplikat: {duplicate_count}
            Temuan pemeriksaan: {findings}
            """

            sample_data = df.head(100).to_string(index=False)

            prompt = f"""
            Kamu adalah ADIWIA, Asisten Digital Audit.

            Lakukan analisis awal terhadap data keuangan berikut.

            INFORMASI DATA:
            {summary}

            DATA TRANSAKSI:
            {sample_data}

            Susun analisis dengan bagian:

            1. Gambaran umum data.
            2. Hasil pemeriksaan data.
            3. Indikasi risiko atau ketidakwajaran.
            4. Hal-hal yang perlu diperiksa auditor.
            5. Rekomendasi tindak lanjut.

            Gunakan bahasa Indonesia yang jelas dan mudah dipahami.

            Jangan menyatakan adanya kecurangan tanpa bukti.
            Bedakan indikasi dan kesimpulan audit.
            """

            result = ask_gemini(prompt)

            st.session_state["audit_result"] = result

    if "audit_result" in st.session_state:

        st.subheader("Hasil Analisis ADIWIA")

        st.markdown(
            st.session_state["audit_result"]
        )


# =====================================================
# 10. DOWNLOAD LAPORAN AUDIT
# =====================================================

st.header("📥 7. Download Laporan Audit")

try:

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Data Transaksi",
            index=False
        )

        pd.DataFrame(
            missing_data,
            columns=["Kolom", "Jumlah Data Kosong"]
        ).to_excel(
            writer,
            sheet_name="Data Kosong",
            index=False
        )

        findings_df.to_excel(
            writer,
            sheet_name="Temuan Audit",
            index=False
        )

        duplicate_rows.to_excel(
            writer,
            sheet_name="Data Duplikat",
            index=False
        )

    output.seek(0)

    st.download_button(
        label="📥 Download Laporan Audit Excel",
        data=output,
        file_name="Laporan_Audit_ADIWIA.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

except Exception as e:

    st.error(f"Gagal membuat laporan: {e}")


# =====================================================
# 11. FOOTER
# =====================================================

st.divider()

st.caption(
    "ADIWIA | Asisten Digital Audit Widianti & Adinda"
)

st.caption(
    "Aplikasi ini membantu pemeriksaan awal data keuangan. "
    "Seluruh hasil tetap memerlukan verifikasi auditor."
)

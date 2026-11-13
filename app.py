
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from io import BytesIO
from google import genai
from dotenv import load_dotenv

# =====================================================
# 1. KONFIGURASI APLIKASI
# =====================================================

st.set_page_config(
    page_title="ADIWIA",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 ADIWIA")
st.subheader("Asisten Digital Audit Widianti & Adinda")

st.write(
    "Asisten digital berbasis Artificial Intelligence "
    "untuk membantu pemeriksaan, analisis, dan evaluasi "
    "data keuangan."
)

st.divider()

# =====================================================
# 2. KONEKSI GEMINI AI
# =====================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

client = None

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.warning(f"Koneksi Gemini belum berhasil: {e}")

MODEL_NAME = "gemini-3.8-flash"

# =====================================================
# 3. UPLOAD DATA AUDIT
# =====================================================

st.header("📂 1. Upload Data Audit")

uploaded_file = st.file_uploader(
    "Unggah data keuangan dalam format Excel",
    type=["xlsx", "xls"]
)

if uploaded_file is None:
    st.info(
        "Silakan unggah file Excel untuk memulai "
        "pemeriksaan menggunakan ADIWIA."
    )
    st.stop()

try:
    df = pd.read_excel(uploaded_file)

    if df.empty:
        st.error("File Excel tidak memiliki data.")
        st.stop()

    if len(df.columns) == 0:
        st.error("File tidak memiliki kolom.")
        st.stop()

except Exception as e:
    st.error(f"Gagal membaca file: {e}")
    st.stop()

st.success("Data berhasil diunggah!")

# =====================================================
# 4. INFORMASI DATA
# =====================================================

st.header("📊 2. Informasi Data")

col1, col2, col3 = st.columns(3)

col1.metric("Jumlah Transaksi", f"{len(df):,}")
col2.metric("Jumlah Kolom", len(df.columns))
col3.metric(
    "Data Kosong",
    int(df.isna().sum().sum())
)

st.subheader("Pratinjau Data")
st.dataframe(df, use_container_width=True)

# =====================================================
# 5. PEMERIKSAAN KELENGKAPAN DATA
# =====================================================

st.header("🔍 3. Pemeriksaan Data Audit")

findings = []
details = {}

# A. Data kosong

missing_count = int(df.isna().sum().sum())

if missing_count > 0:
    for column, count in df.isna().items():
        if count:
            findings.append({
                "Jenis Temuan": "Data Tidak Lengkap",
                "Kolom": str(column),
                "Jumlah": int(count),
                "Keterangan": (
                    f"Terdapat {count} data kosong "
                    f"pada kolom {column}."
                )
            })

details["Data Tidak Lengkap"] = df[
    df.isna().any(axis=1)
]

# B. Data duplikat

duplicate_mask = df.duplicated(keep=False)

duplicate_count = int(duplicate_mask.sum())

if duplicate_count > 0:
    findings.append({
        "Jenis Temuan": "Data Duplikat",
        "Kolom": "Seluruh kolom",
        "Jumlah": duplicate_count,
        "Keterangan": (
            "Terdapat baris transaksi yang memiliki "
            "data identik dan perlu diverifikasi."
        )
    })

details["Data Duplikat"] = df[duplicate_mask]

# =====================================================
# 6. PEMERIKSAAN NOMINAL TIDAK WAJAR
# =====================================================

st.subheader("Pemeriksaan Nominal Transaksi")

numeric_columns = df.select_dtypes(
    include=np.number
).columns.tolist()

amount_candidates = [
    col for col in numeric_columns
    if any(
        word in str(col).lower()
        for word in [
            "nominal", "jumlah", "amount",
            "nilai", "actual", "realisasi"
        ]
    )
]

unusual_mask = pd.Series(False, index=df.index)

if amount_candidates:

    amount_column = st.selectbox(
        "Pilih kolom nominal yang akan diperiksa",
        amount_candidates
    )

    amount_values = pd.to_numeric(
        df[amount_column],
        errors="coerce"
    ).dropna()

    if len(amount_values) >= 4:

        q1 = amount_values.quantile(0.25)
        q3 = amount_values.quantile(0.75)
        iqr = q3 - q1

        lower_limit = q1 - (1.5 * iqr)
        upper_limit = q3 + (1.5 * iqr)

        numeric_values = pd.to_numeric(
            df[amount_column],
            errors="coerce"
        )

        unusual_mask = (
            (numeric_values < lower_limit) |
            (numeric_values > upper_limit)
        ).fillna(False)

        unusual_count = int(unusual_mask.sum())

        if unusual_count > 0:
            findings.append({
                "Jenis Temuan": "Nominal Tidak Wajar",
                "Kolom": str(amount_column),
                "Jumlah": unusual_count,
                "Keterangan": (
                    "Nominal berada di luar batas statistik "
                    "metode Interquartile Range (IQR)."
                )
            })

    else:
        st.info(
            "Data nominal belum cukup untuk analisis IQR."
        )

else:
    st.info(
        "Tidak ditemukan kolom nominal yang dikenali. "
        "Periksa nama kolom pada file Excel."
    )

details["Nominal Tidak Wajar"] = df[unusual_mask]

# =====================================================
# 7. PEMERIKSAAN DEBIT DAN KREDIT
# =====================================================

st.subheader("Pemeriksaan Debit dan Kredit")

debit_columns = [
    col for col in numeric_columns
    if "debit" in str(col).lower()
]

credit_columns = [
    col for col in numeric_columns
    if "kredit" in str(col).lower()
    or "credit" in str(col).lower()
]

imbalance_mask = pd.Series(False, index=df.index)

if debit_columns and credit_columns:

    debit_col = debit_columns[0]
    credit_col = credit_columns[0]

    debit = pd.to_numeric(
        df[debit_col],
        errors="coerce"
    )

    credit = pd.to_numeric(
        df[credit_col],
        errors="coerce"
    )

    imbalance_mask = (
        debit.notna() &
        credit.notna() &
        ~np.isclose(
            debit.fillna(0),
            credit.fillna(0),
            atol=0.01
        )
    )

    imbalance_count = int(imbalance_mask.sum())

    if imbalance_count > 0:
        findings.append({
            "Jenis Temuan": "Debit dan Kredit Tidak Seimbang",
            "Kolom": f"{debit_col} dan {credit_col}",
            "Jumlah": imbalance_count,
            "Keterangan": (
                "Ditemukan perbedaan nilai debit "
                "dan kredit pada baris transaksi."
            )
        })

    details["Debit dan Kredit"] = df[imbalance_mask]

else:
    st.info(
        "Pemeriksaan debit dan kredit dilewati karena "
        "kolom debit atau kredit tidak tersedia."
    )

# =====================================================
# 8. ANALISIS ANGGARAN DAN REALISASI
# =====================================================

st.divider()
st.header("💰 4. Analisis Anggaran dan Realisasi")

budget_columns = [
    col for col in df.columns
    if str(col).lower() == "budget"
]

actual_columns = [
    col for col in df.columns
    if str(col).lower() == "actual"
]

budget_available = bool(budget_columns)
actual_available = bool(actual_columns)

if budget_available and actual_available:

    df["Budget"] = pd.to_numeric(
        df["Budget"], errors="coerce"
    )

    df["Actual"] = pd.to_numeric(
        df["Actual"], errors="coerce"
    )

    if df[["Budget", "Actual"]].isna().any().any():
        st.warning(
            "Ada nilai Budget atau Actual yang kosong "
            "atau tidak valid. Periksa kembali datanya."
        )
        budget_available = False

    else:

        df["Variance"] = df["Actual"] - df["Budget"]

        df["Variance %"] = np.where(
            df["Budget"] != 0,
            df["Variance"] / df["Budget"] * 100,
            np.nan
        )

        total_budget = df["Budget"].sum()
        total_actual = df["Actual"].sum()
        total_variance = total_actual - total_budget

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Total Anggaran",
            f"{total_budget:,.2f}"
        )

        c2.metric(
            "Total Realisasi",
            f"{total_actual:,.2f}"
        )

        c3.metric(
            "Selisih",
            f"{total_variance:,.2f}"
        )

        st.subheader("Hasil Perhitungan Varians")

        st.dataframe(
            df,
            use_container_width=True
        )

        # Grafik anggaran dan realisasi

        category_columns = [
            col for col in df.columns
            if str(col).lower() == "category"
        ]

        if category_columns:

            fig = px.bar(
                df,
                x="Category",
                y=["Budget", "Actual"],
                barmode="group",
                title="Perbandingan Anggaran dan Realisasi"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        # Grafik selisih

        if category_columns:

            fig_variance = px.bar(
                df,
                x="Category",
                y="Variance",
                color="Variance",
                title="Analisis Varians per Kategori",
                color_continuous_scale="RdYlGn"
            )

            st.plotly_chart(
                fig_variance,
                use_container_width=True
            )

        # Temuan anggaran

        overspending = df[df["Actual"] > df["Budget"]]

        if not overspending.empty:
            findings.append({
                "Jenis Temuan": "Realisasi Melebihi Anggaran",
                "Kolom": "Actual dan Budget",
                "Jumlah": len(overspending),
                "Keterangan": (
                    "Terdapat kategori dengan realisasi "
                    "lebih besar daripada anggaran."
                )
            })

        details["Realisasi Melebihi Anggaran"] = overspending

else:
    st.info(
        "Analisis anggaran dan realisasi memerlukan "
        "kolom bernama Budget dan Actual."
    )

# =====================================================
# 9. RINGKASAN TEMUAN AUDIT
# =====================================================

st.divider()
st.header("🚨 5. Ringkasan Temuan Audit")

result = pd.DataFrame(
    findings,
    columns=[
        "Jenis Temuan",
        "Kolom",
        "Jumlah",
        "Keterangan"
    ]
)

if not result.empty:

    st.warning(
        f"Terdapat {len(result)} jenis indikasi "
        "yang perlu diperiksa lebih lanjut."
    )

    st.dataframe(
        result,
        use_container_width=True
    )

else:
    st.success(
        "Tidak ditemukan indikasi berdasarkan "
        "pemeriksaan otomatis yang dilakukan."
    )

for title, detail in details.items():

    if not detail.empty:

        with st.expander(f"📋 Lihat detail: {title}"):

            st.dataframe(
                detail,
                use_container_width=True
            )

# =====================================================
# 10. AI-POWERED AUDIT ANALYSIS
# =====================================================

st.divider()
st.header("🤖 6. AI Audit Analysis")

if client:

    if st.button("Analisis Temuan dengan ADIWIA AI"):

        with st.spinner(
            "ADIWIA sedang menganalisis data audit..."
        ):

            prompt = f"""
            Anda adalah ADIWIA, asisten digital audit
            yang membantu analisis data keuangan.

            Analisis data berikut:

            DATA:
            {df.head(200).to_string(index=False)}

            TEMUAN PEMERIKSAAN:
            {result.to_string(index=False)}

            Berikan hasil dalam struktur:

            1. Ringkasan hasil pemeriksaan.
            2. Temuan yang paling perlu diperhatikan.
            3. Analisis risiko.
            4. Kemungkinan penyebab yang perlu ditelusuri.
            5. Dokumen atau bukti pendukung yang perlu diperiksa.
            6. Rekomendasi tindak lanjut.

            Ketentuan:
            - Gunakan bahasa Indonesia yang jelas.
            - Bedakan fakta data dan dugaan.
            - Jangan mengarang penyebab atau bukti.
            - Jangan langsung menyimpulkan kecurangan.
            - Hasil adalah indikasi awal, bukan opini audit.
            """

            try:

                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt
                )

                st.markdown(response.text)

            except Exception as e:
                st.error(f"Gemini API Error: {e}")

else:

    st.warning(
        "Fitur AI belum aktif. Tambahkan Gemini API Key "
        "pada Streamlit Secrets untuk menggunakannya."
    )

# =====================================================
# 11. DOWNLOAD LAPORAN AUDIT
# =====================================================

st.divider()
st.header("📥 8. Download Laporan Audit")

output = BytesIO()

with pd.ExcelWriter(
    output,
    engine="openpyxl"
) as writer:

    df.to_excel(
        writer,
        sheet_name="Data Audit",
        index=False
    )

    result.to_excel(
        writer,
        sheet_name="Temuan Audit",
        index=False
    )

st.download_button(
    label="Download Laporan ADIWIA (Excel)",
    data=output.getvalue(),
    file_name="Laporan_Audit_ADIWIA.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    )
)

# =====================================================
# 12. FOOTER
# =====================================================

st.divider()

st.caption(
    "ADIWIA | Asisten Digital Audit Widianti & Adinda"
)

st.caption(
    "Sistem pendukung pemeriksaan audit. "
    "Seluruh indikasi temuan harus diverifikasi "
    "oleh auditor sebelum dijadikan kesimpulan."
)

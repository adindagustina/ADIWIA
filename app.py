
import os
import time
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from google import genai


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
# 2. FUNGSI PENDUKUNG
# =====================================================

def normalize_column(name):
    """Menyeragamkan nama kolom."""

    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_column(columns, aliases):
    """Mencari kolom berdasarkan beberapa nama alternatif."""

    lookup = {
        normalize_column(col): col
        for col in columns
    }

    for alias in aliases:
        key = normalize_column(alias)

        if key in lookup:
            return lookup[key]

    return None


def ask_gemini(prompt, retries=3):
    """Mengirim permintaan analisis kepada Gemini."""

    if client is None:
        return "Gemini API belum dikonfigurasi. Periksa API Key di Streamlit Secrets."

    for attempt in range(retries):

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            return response.text or "Gemini tidak memberikan hasil analisis."

        except Exception as e:

            error_message = str(e)

            temporary_error = any(
                code in error_message
                for code in ["503", "429", "500", "504", "UNAVAILABLE"]
            )

            if temporary_error and attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue

            return f"Analisis AI belum berhasil. Keterangan: {error_message}"

    return "Analisis AI belum berhasil. Silakan coba kembali."


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
    "Unggah file data audit dalam format Excel",
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

    if len(df.columns) == 0:
        st.warning("Tidak ditemukan kolom pada file Excel.")
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

col1.metric("Jumlah Transaksi", f"{total_transaksi:,}")
col2.metric("Jumlah Kolom", f"{total_kolom:,}")
col3.metric("Data Kosong", f"{total_kosong:,}")

st.subheader("Nama Kolom Data")

st.write(", ".join(map(str, df.columns)))

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

st.subheader("A. Pemeriksaan Data Kosong")

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

st.subheader("B. Pemeriksaan Data Duplikat")

duplicate_count = int(df.duplicated().sum())

duplicate_rows = df[df.duplicated(keep=False)]

if duplicate_count > 0:

    st.warning(
        f"Ditemukan {duplicate_count} baris data duplikat."
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

    st.success("Tidak ditemukan data duplikat.")


# -----------------------------------------------------
# C. PEMERIKSAAN NOMINAL TIDAK WAJAR
# -----------------------------------------------------

st.subheader("C. Pemeriksaan Nominal Tidak Wajar")

numeric_columns = df.select_dtypes(
    include="number"
).columns.tolist()

amount_aliases = [
    "amount",
    "amount_usd",
    "nominal",
    "jumlah",
    "nilai",
    "total",
    "realisasi",
    "pengeluaran"
]

if numeric_columns:

    amount_suggestion = find_column(
        numeric_columns,
        amount_aliases
    )

    default_index = (
        numeric_columns.index(amount_suggestion)
        if amount_suggestion in numeric_columns
        else 0
    )

    amount_column = st.selectbox(
        "Pilih kolom nominal yang akan diperiksa",
        numeric_columns,
        index=default_index,
        key="amount_column"
    )

    amount_values = pd.to_numeric(
        df[amount_column],
        errors="coerce"
    )

    valid_values = amount_values.dropna()

    if len(valid_values) >= 4:

        q1 = valid_values.quantile(0.25)
        q3 = valid_values.quantile(0.75)
        iqr = q3 - q1

        if iqr > 0:

            lower_limit = q1 - (1.5 * iqr)
            upper_limit = q3 + (1.5 * iqr)

            outlier_mask = (
                (amount_values < lower_limit)
                | (amount_values > upper_limit)
            )

            outlier_data = df[outlier_mask]

            if not outlier_data.empty:

                st.warning(
                    f"Ditemukan {len(outlier_data)} transaksi "
                    "dengan nilai di luar batas IQR."
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
                "Nilai pada kolom tersebut relatif sama. "
                "Pemeriksaan IQR tidak dapat dilakukan."
            )

    else:

        st.info(
            "Data angka belum cukup untuk pemeriksaan IQR."
        )

else:

    st.info(
        "Tidak ditemukan kolom numerik untuk pemeriksaan nominal."
    )


# -----------------------------------------------------
# D. PEMERIKSAAN DEBIT DAN KREDIT
# -----------------------------------------------------

st.subheader("D. Pemeriksaan Keseimbangan Debit dan Kredit")

debit_aliases = [
    "debit",
    "debet",
    "debit_amount",
    "jumlah_debit",
    "debit_rp",
    "nilai_debit"
]

credit_aliases = [
    "credit",
    "kredit",
    "credit_amount",
    "jumlah_kredit",
    "kredit_rp",
    "nilai_kredit"
]

debit_suggestion = find_column(
    numeric_columns,
    debit_aliases
)

credit_suggestion = find_column(
    numeric_columns,
    credit_aliases
)

debit_options = ["Tidak digunakan"] + numeric_columns
credit_options = ["Tidak digunakan"] + numeric_columns

debit_index = (
    debit_options.index(debit_suggestion)
    if debit_suggestion in debit_options
    else 0
)

credit_index = (
    credit_options.index(credit_suggestion)
    if credit_suggestion in credit_options
    else 0
)

col1, col2 = st.columns(2)

with col1:

    debit_choice = st.selectbox(
        "Pilih kolom Debit",
        debit_options,
        index=debit_index,
        key="debit_choice"
    )

with col2:

    credit_choice = st.selectbox(
        "Pilih kolom Kredit",
        credit_options,
        index=credit_index,
        key="credit_choice"
    )

if (
    debit_choice != "Tidak digunakan"
    and credit_choice != "Tidak digunakan"
    and debit_choice != credit_choice
):

    debit_values = pd.to_numeric(
        df[debit_choice],
        errors="coerce"
    )

    credit_values = pd.to_numeric(
        df[credit_choice],
        errors="coerce"
    )

    debit_total = debit_values.sum()
    credit_total = credit_values.sum()

    difference = debit_total - credit_total

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Debit", f"{debit_total:,.2f}")
    col2.metric("Total Kredit", f"{credit_total:,.2f}")
    col3.metric("Selisih", f"{difference:,.2f}")

    if abs(difference) < 0.01:

        st.success("Total debit dan kredit seimbang.")

    else:

        st.warning("Total debit dan kredit tidak seimbang.")

        findings.append({
            "Jenis Temuan": "Debit dan Kredit Tidak Seimbang",
            "Keterangan": (
                f"Selisih total debit dan kredit sebesar "
                f"{difference:,.2f}."
            )
        })

elif (
    debit_choice != "Tidak digunakan"
    and debit_choice == credit_choice
):

    st.warning("Pilih kolom debit dan kredit yang berbeda.")

else:

    st.info(
        "Pilih kolom debit dan kredit jika tersedia. "
        "Pemeriksaan dapat dilewati jika data tidak memilikinya."
    )


# =====================================================
# 7. ANALISIS ANGGARAN DAN REALISASI
# =====================================================

st.header("💰 4. Analisis Anggaran dan Realisasi")

budget_aliases = [
    "budget",
    "anggaran",
    "pagu",
    "jumlah_anggaran",
    "nilai_anggaran"
]

actual_aliases = [
    "actual",
    "realisasi",
    "pengeluaran",
    "jumlah_realisasi",
    "nilai_realisasi"
]

budget_suggestion = find_column(
    numeric_columns,
    budget_aliases
)

actual_suggestion = find_column(
    numeric_columns,
    actual_aliases
)

if len(numeric_columns) >= 2:

    budget_options = ["Pilih kolom"] + numeric_columns

    budget_index = (
        budget_options.index(budget_suggestion)
        if budget_suggestion in budget_options
        else 0
    )

    actual_index = (
        budget_options.index(actual_suggestion)
        if actual_suggestion in budget_options
        else 0
    )

    col1, col2 = st.columns(2)

    with col1:

        budget_choice = st.selectbox(
            "Pilih kolom Anggaran",
            budget_options,
            index=budget_index,
            key="budget_choice"
        )

    with col2:

        actual_choice = st.selectbox(
            "Pilih kolom Realisasi",
            budget_options,
            index=actual_index,
            key="actual_choice"
        )

    if (
        budget_choice != "Pilih kolom"
        and actual_choice != "Pilih kolom"
        and budget_choice != actual_choice
    ):

        budget_values = pd.to_numeric(
            df[budget_choice],
            errors="coerce"
        )

        actual_values = pd.to_numeric(
            df[actual_choice],
            errors="coerce"
        )

        comparison = pd.DataFrame({
            "Anggaran": budget_values,
            "Realisasi": actual_values
        })

        comparison["Selisih"] = (
            comparison["Realisasi"]
            - comparison["Anggaran"]
        )

        comparison["Persentase Realisasi"] = (
            comparison["Realisasi"]
            / comparison["Anggaran"].replace(0, float("nan"))
        ) * 100

        total_budget = budget_values.sum()
        total_actual = actual_values.sum()

        total_difference = total_actual - total_budget

        percentage = (
            total_actual / total_budget * 100
            if total_budget != 0
            else 0
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Total Anggaran",
            f"{total_budget:,.2f}"
        )

        col2.metric(
            "Total Realisasi",
            f"{total_actual:,.2f}"
        )

        col3.metric(
            "Persentase Realisasi",
            f"{percentage:,.2f}%"
        )

        st.subheader("Grafik Anggaran dan Realisasi")

        chart_df = pd.DataFrame({
            "Jenis": ["Anggaran", "Realisasi"],
            "Jumlah": [total_budget, total_actual]
        })

        fig = px.bar(
            chart_df,
            x="Jenis",
            y="Jumlah",
            color="Jenis",
            title="Perbandingan Total Anggaran dan Realisasi"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.subheader("Detail Perbandingan")

        st.dataframe(
            comparison,
            use_container_width=True
        )

        if total_difference > 0:

            st.warning(
                f"Realisasi melebihi anggaran sebesar "
                f"{total_difference:,.2f}."
            )

            findings.append({
                "Jenis Temuan": "Realisasi Melebihi Anggaran",
                "Keterangan": (
                    f"Realisasi lebih besar daripada anggaran "
                    f"sebesar {total_difference:,.2f}."
                )
            })

        else:

            st.success(
                "Total realisasi tidak melebihi total anggaran."
            )

    elif (
        budget_choice != "Pilih kolom"
        and budget_choice == actual_choice
    ):

        st.warning(
            "Kolom anggaran dan realisasi harus berbeda."
        )

    else:

        st.info(
            "Pilih kolom anggaran dan realisasi untuk memulai analisis."
        )

else:

    st.info(
        "Analisis anggaran dan realisasi memerlukan minimal "
        "dua kolom numerik."
    )


# =====================================================
# 8. RINGKASAN TEMUAN AUDIT
# =====================================================

st.header("🚨 5. Ringkasan Temuan Audit")

findings_df = pd.DataFrame(
    findings,
    columns=["Jenis Temuan", "Keterangan"]
)

if not findings_df.empty:

    st.warning(
        f"Ditemukan {len(findings_df)} indikasi "
        "yang perlu diperiksa lebih lanjut."
    )

    st.dataframe(
        findings_df,
        use_container_width=True
    )

else:

    st.success(
        "Tidak ditemukan indikasi berdasarkan pemeriksaan "
        "otomatis yang telah dilakukan."
    )

st.caption(
    "Hasil pemeriksaan merupakan indikasi awal dan tetap "
    "memerlukan verifikasi auditor."
)


# =====================================================
# 9. AI AUDIT ANALYSIS
# =====================================================

st.header("🤖 6. AI Audit Analysis")

if client is None:

    st.warning(
        "Fitur AI belum aktif. Periksa Gemini API Key "
        "pada Streamlit Secrets."
    )

else:

    st.info(
        "Gunakan fitur ini untuk memperoleh analisis awal "
        "berdasarkan data dan hasil pemeriksaan."
    )

    if st.button("Mulai Analisis AI", type="primary"):

        with st.spinner("ADIWIA sedang menganalisis data..."):

            summary = f"""
Jumlah transaksi: {total_transaksi}
Jumlah kolom: {total_kolom}
Jumlah data kosong: {total_kosong}
Jumlah baris duplikat: {duplicate_count}

Temuan pemeriksaan:
{findings_df.to_string(index=False)}
"""

            sample_data = df.head(100).to_string(index=False)

            prompt = f"""
Kamu adalah ADIWIA, Asisten Digital Audit.

Lakukan analisis awal terhadap data keuangan berikut.

INFORMASI DATA:
{summary}

DATA TRANSAKSI:
{sample_data}

Susun hasil analisis dengan bagian:

1. Gambaran umum data.
2. Hasil pemeriksaan data.
3. Indikasi risiko atau ketidakwajaran.
4. Hal-hal yang perlu diperiksa auditor.
5. Rekomendasi tindak lanjut.

Gunakan bahasa Indonesia yang jelas dan mudah dipahami.

Jangan menyatakan adanya kecurangan tanpa bukti.
Bedakan indikasi dan kesimpulan audit.
Jangan mengarang informasi yang tidak terdapat dalam data.
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
        data=output.getvalue(),
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

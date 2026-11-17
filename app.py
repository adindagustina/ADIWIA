
# =====================================================
# DASHBOARD ADIWIA
# =====================================================

st.markdown("""
<style>
.dashboard-header {
    background: linear-gradient(120deg, #101D35, #243B5A);
    padding: 28px;
    border-radius: 15px;
    color: white;
    margin-bottom: 25px;
}

.logo-container {
    display: flex;
    align-items: center;
    gap: 17px;
}

.logo-icon {
    width: 68px;
    height: 68px;
    background: linear-gradient(135deg, #D6B66D, #F3DFA5);
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #101D35;
    font-size: 35px;
    font-weight: 800;
    font-family: Georgia, serif;
}

.logo-title {
    font-size: 29px;
    font-weight: 800;
    letter-spacing: 3px;
    margin: 0;
}

.logo-subtitle {
    font-size: 13px;
    color: #D8DFE9;
    margin-top: 5px;
}

.metric-card {
    background: white;
    border: 1px solid #E5E9F0;
    border-radius: 12px;
    padding: 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.metric-label {
    color: #64748B;
    font-size: 13px;
    margin-bottom: 8px;
}

.metric-value {
    color: #14243D;
    font-size: 27px;
    font-weight: 750;
}

.section-title {
    color: #14243D;
    font-size: 19px;
    font-weight: 700;
    margin-top: 15px;
    margin-bottom: 15px;
}

</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------
# LOGO DAN HEADER
# -----------------------------------------------------

st.markdown("""
<div class="dashboard-header">
    <div class="logo-container">
        <div class="logo-icon">A</div>
        <div>
            <div class="logo-title">ADIWIA</div>
            <div class="logo-subtitle">
                Asisten Digital Audit Widianti & Adinda
            </div>
            <div class="logo-subtitle">
                Artificial Intelligence for Audit Assistance
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------
# DASHBOARD
# -----------------------------------------------------

st.subheader("Dashboard Audit")
st.caption("Ringkasan informasi dan hasil pemeriksaan data keuangan.")


if "df" in locals() and df is not None:

    # Menghitung informasi data
    total_transaksi = len(df)
    total_kolom = len(df.columns)
    total_data_kosong = int(df.isna().sum().sum())
    total_duplikat = int(df.duplicated().sum())

    # Menghitung outlier menggunakan IQR
    total_outlier = 0

    for col in df.select_dtypes(include="number").columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1

        if IQR > 0:
            batas_bawah = Q1 - 1.5 * IQR
            batas_atas = Q3 + 1.5 * IQR

            total_outlier += int(
                ((df[col] < batas_bawah) |
                 (df[col] > batas_atas)).sum()
            )

    # Menghitung jumlah temuan
    total_temuan = 0

    if "findings_df" in locals() and isinstance(findings_df, pd.DataFrame):
        total_temuan = len(findings_df)

    # -------------------------------------------------
    # KARTU RINGKASAN
    # -------------------------------------------------

    st.markdown('<div class="section-title">Ringkasan Data Audit</div>',
                unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Transaksi", f"{total_transaksi:,}")

    with col2:
        st.metric("Jumlah Kolom", f"{total_kolom:,}")

    with col3:
        st.metric("Total Temuan", f"{total_temuan:,}")

    col4, col5, col6 = st.columns(3)

    with col4:
        st.metric("Data Kosong", f"{total_data_kosong:,}")

    with col5:
        st.metric("Data Duplikat", f"{total_duplikat:,}")

    with col6:
        st.metric("Data Outlier", f"{total_outlier:,}")

    st.divider()

    # -------------------------------------------------
    # GRAFIK TEMUAN AUDIT
    # -------------------------------------------------

    st.markdown('<div class="section-title">Grafik Hasil Pemeriksaan</div>',
                unsafe_allow_html=True)

    ringkasan = pd.DataFrame({
        "Jenis Pemeriksaan": [
            "Data Kosong",
            "Data Duplikat",
            "Data Outlier"
        ],
        "Jumlah Temuan": [
            total_data_kosong,
            total_duplikat,
            total_outlier
        ]
    })

    fig = px.bar(
        ringkasan,
        x="Jenis Pemeriksaan",
        y="Jumlah Temuan",
        text="Jumlah Temuan",
        color="Jenis Pemeriksaan",
        color_discrete_sequence=[
            "#243B5A",
            "#C5A45D",
            "#7186A5"
        ],
        title="Ringkasan Temuan Pemeriksaan Data"
    )

    fig.update_layout(
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#243B5A"),
        yaxis_title="Jumlah",
        xaxis_title="",
        margin=dict(t=50, b=20)
    )

    fig.update_traces(
        textposition="outside"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # -------------------------------------------------
    # STATUS PEMERIKSAAN
    # -------------------------------------------------

    st.markdown('<div class="section-title">Status Pemeriksaan Audit</div>',
                unsafe_allow_html=True)

    if total_data_kosong > 0 or total_duplikat > 0 or total_outlier > 0 or total_temuan > 0:

        st.warning(
            "Terdapat data yang memerlukan pemeriksaan dan tindak lanjut lebih lanjut."
        )

    else:

        st.success(
            "Tidak ditemukan indikasi masalah berdasarkan pemeriksaan awal."
        )

    st.caption(
        "Catatan: Hasil pemeriksaan merupakan indikasi awal dan tetap memerlukan verifikasi auditor."
    )

else:

    st.info(
        "Silakan unggah file Excel terlebih dahulu untuk menampilkan Dashboard ADIWIA."
    )

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

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # 1. Seluruh Data Transaksi
        df.to_excel(
            writer,
            sheet_name="Data Transaksi",
            index=False
        )

        # 2. Data Kosong
        pd.DataFrame(
            missing_data,
            columns=["Kolom", "Jumlah Data Kosong"]
        ).to_excel(
            writer,
            sheet_name="Data Kosong",
            index=False
        )

        # 3. Seluruh Temuan Audit
        findings_df.to_excel(
            writer,
            sheet_name="Ringkasan Temuan",
            index=False
        )

        # 4. Data Duplikat
        duplicate_rows.to_excel(
            writer,
            sheet_name="Data Duplikat",
            index=False
        )

        # 5. Data Outlier
        outlier_report = pd.DataFrame()

        if "outlier_rows" in locals() and isinstance(outlier_rows, pd.DataFrame):
            outlier_report = outlier_rows

        outlier_report.to_excel(
            writer,
            sheet_name="Data Outlier",
            index=False
        )

        # 6. Hasil Pemeriksaan Debit dan Kredit
        debit_credit_report = pd.DataFrame()

        if "debit_total" in locals() and "credit_total" in locals():
            debit_credit_report = pd.DataFrame({
                "Keterangan": [
                    "Total Debit",
                    "Total Kredit",
                    "Selisih"
                ],
                "Jumlah": [
                    debit_total,
                    credit_total,
                    debit_total - credit_total
                ]
            })

        debit_credit_report.to_excel(
            writer,
            sheet_name="Pemeriksaan Debit Kredit",
            index=False
        )

        # 7. Perbandingan Anggaran dan Realisasi
        budget_report = pd.DataFrame()

        if "budget_df" in locals() and isinstance(budget_df, pd.DataFrame):
            budget_report = budget_df

        budget_report.to_excel(
            writer,
            sheet_name="Anggaran Realisasi",
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

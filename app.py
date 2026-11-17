
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
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

try:
    API_KEY = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    API_KEY = os.getenv("GEMINI_API_KEY", "")


# =====================================================
# 2. DESAIN DAN CSS
# =====================================================

st.markdown("""
<style>

.stApp {
    background-color: #F5F7FB;
}

[data-testid="stSidebar"] {
    background-color: #14243A;
}

[data-testid="stSidebar"] * {
    color: white;
}

.main-title {
    font-size: 30px;
    font-weight: 800;
    color: #14243A;
}

.sub-title {
    color: #64748B;
    font-size: 14px;
}

.brand-logo {
    width: 65px;
    height: 65px;
    background: #D6AE58;
    color: #14243A;
    border-radius: 15px;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 25px;
    font-weight: 900;
    margin: auto;
}

.hero {
    background: linear-gradient(120deg, #14243A, #243F60);
    padding: 35px;
    border-radius: 18px;
    color: white;
    margin-bottom: 25px;
}

.hero h1 {
    color: white;
    font-size: 34px;
}

.hero p {
    color: #E3EAF2;
    font-size: 16px;
    line-height: 1.7;
}

.section-card {
    background: white;
    padding: 22px;
    border-radius: 14px;
    border: 1px solid #E5EAF1;
    min-height: 160px;
}

.section-card h4 {
    color: #14243A;
}

.section-card p {
    color: #64748B;
    font-size: 14px;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #E5EAF1;
}

.metric-label {
    color: #64748B;
    font-size: 13px;
}

.metric-value {
    color: #14243A;
    font-size: 25px;
    font-weight: bold;
}

.footer {
    text-align: center;
    color: #94A3B8;
    font-size: 12px;
    padding: 25px;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# 3. SESSION STATE
# =====================================================

if "audit_df" not in st.session_state:
    st.session_state.audit_df = None

if "ai_result" not in st.session_state:
    st.session_state.ai_result = None

if "file_name" not in st.session_state:
    st.session_state.file_name = ""

if "debit_choice" not in st.session_state:
    st.session_state.debit_choice = None

if "credit_choice" not in st.session_state:
    st.session_state.credit_choice = None

if "budget_choice" not in st.session_state:
    st.session_state.budget_choice = None

if "actual_choice" not in st.session_state:
    st.session_state.actual_choice = None


# =====================================================
# 4. FUNGSI PENDUKUNG
# =====================================================

def format_rupiah(value):
    try:
        return "Rp {:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return "Rp 0"


def get_numeric_columns(data):
    return data.select_dtypes(include="number").columns.tolist()


def get_outlier_data(data):
    hasil = []
    daftar_outlier = []

    numeric_columns = get_numeric_columns(data)

    for column in numeric_columns:
        values = pd.to_numeric(data[column], errors="coerce").dropna()

        if len(values) < 4:
            continue

        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1

        batas_bawah = q1 - (1.5 * iqr)
        batas_atas = q3 + (1.5 * iqr)

        mask = (
            (pd.to_numeric(data[column], errors="coerce") < batas_bawah) |
            (pd.to_numeric(data[column], errors="coerce") > batas_atas)
        )

        outlier = data[mask].copy()

        if not outlier.empty:
            hasil.append({
                "Kolom": column,
                "Jumlah Outlier": len(outlier),
                "Batas Bawah": batas_bawah,
                "Batas Atas": batas_atas
            })

            outlier["Kolom Pemeriksaan"] = column
            daftar_outlier.append(outlier)

    hasil_df = pd.DataFrame(hasil)

    if daftar_outlier:
        outlier_df = pd.concat(daftar_outlier, ignore_index=True)
    else:
        outlier_df = pd.DataFrame()

    return hasil_df, outlier_df


def ask_gemini(prompt):
    if not API_KEY:
        return (
            "API Key Gemini belum ditemukan. "
            "Silakan masukkan GEMINI_API_KEY pada bagian Secrets "
            "di pengaturan aplikasi Streamlit."
        )

    try:
        client = genai.Client(api_key=API_KEY)

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt
                )

                if response.text:
                    return response.text

                return "AI tidak memberikan jawaban. Silakan coba kembali."

            except Exception as error:
                error_text = str(error)

                if any(code in error_text for code in ["503", "429", "500", "504"]):
                    if attempt < 2:
                        time.sleep(2 ** (attempt + 1))
                        continue

                return f"Analisis AI belum berhasil dilakukan.\n\nDetail: {error_text}"

    except Exception as error:
        return f"Terjadi kesalahan saat menghubungkan ke Gemini: {error}"


def buat_ringkasan_temuan(data):
    findings = []

    # Pemeriksaan data kosong
    missing = data.isna().sum()
    total_missing = int(missing.sum())

    if total_missing > 0:
        findings.append({
            "Jenis Temuan": "Data Kosong",
            "Keterangan": f"Ditemukan {total_missing} sel data kosong dalam dataset."
        })

    # Pemeriksaan data duplikat
    total_duplicate = int(data.duplicated().sum())

    if total_duplicate > 0:
        findings.append({
            "Jenis Temuan": "Data Duplikat",
            "Keterangan": f"Ditemukan {total_duplicate} baris data duplikat."
        })

    # Pemeriksaan outlier
    outlier_summary, _ = get_outlier_data(data)

    total_outlier = (
        int(outlier_summary["Jumlah Outlier"].sum())
        if not outlier_summary.empty else 0
    )

    if total_outlier > 0:
        findings.append({
            "Jenis Temuan": "Data Outlier",
            "Keterangan": (
                f"Ditemukan {total_outlier} nilai outlier "
                "berdasarkan metode Interquartile Range (IQR)."
            )
        })

    # Pemeriksaan debit dan kredit
    debit_col = st.session_state.debit_choice
    credit_col = st.session_state.credit_choice

    if (
        debit_col in data.columns
        and credit_col in data.columns
        and debit_col != credit_col
    ):
        total_debit = pd.to_numeric(
            data[debit_col], errors="coerce"
        ).fillna(0).sum()

        total_credit = pd.to_numeric(
            data[credit_col], errors="coerce"
        ).fillna(0).sum()

        selisih = abs(total_debit - total_credit)

        if selisih > 0.01:
            findings.append({
                "Jenis Temuan": "Ketidakseimbangan Debit dan Kredit",
                "Keterangan": (
                    f"Total debit {format_rupiah(total_debit)} "
                    f"dan total kredit {format_rupiah(total_credit)} "
                    f"memiliki selisih {format_rupiah(selisih)}."
                )
            })

    # Pemeriksaan anggaran dan realisasi
    budget_col = st.session_state.budget_choice
    actual_col = st.session_state.actual_choice

    if (
        budget_col in data.columns
        and actual_col in data.columns
        and budget_col != actual_col
    ):
        anggaran = pd.to_numeric(
            data[budget_col], errors="coerce"
        ).fillna(0).sum()

        realisasi = pd.to_numeric(
            data[actual_col], errors="coerce"
        ).fillna(0).sum()

        if realisasi > anggaran:
            findings.append({
                "Jenis Temuan": "Realisasi Melebihi Anggaran",
                "Keterangan": (
                    f"Total realisasi melebihi anggaran sebesar "
                    f"{format_rupiah(realisasi - anggaran)}."
                )
            })

    if not findings:
        findings.append({
            "Jenis Temuan": "Tidak Ada Temuan Otomatis",
            "Keterangan": (
                "Tidak ditemukan indikasi masalah berdasarkan "
                "pemeriksaan otomatis yang tersedia."
            )
        })

    return pd.DataFrame(findings)


# =====================================================
# 5. SIDEBAR DAN NAVIGASI
# =====================================================

with st.sidebar:

    st.markdown("""
    <div style="text-align:center; padding:20px 5px;">
        <div class="brand-logo">AW</div>
        <h2 style="color:white; margin-top:12px;">ADIWIA</h2>
        <p style="font-size:11px; color:#CBD5E1;">
            Asisten Digital Audit<br>
            Widianti & Adinda
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    menu = st.radio(
        "MENU UTAMA",
        [
            "Dashboard",
            "Upload Data Audit",
            "Informasi Data",
            "Pemeriksaan Data Audit",
            "Analisis Anggaran dan Realisasi",
            "Ringkasan Temuan Audit",
            "AI Audit Analysis",
            "Download Laporan Audit"
        ],
        label_visibility="visible"
    )

    st.markdown("---")

    st.caption("ADIWIA | Digital Audit Assistant")


# =====================================================
# 6. PERSIAPAN DATA
# =====================================================

df = st.session_state.audit_df

if df is not None:

    total_rows = len(df)
    total_columns = len(df.columns)

    missing_data = df.isna().sum().reset_index()
    missing_data.columns = ["Kolom", "Jumlah Data Kosong"]
    missing_data = missing_data[missing_data["Jumlah Data Kosong"] > 0]

    duplicate_data = df[df.duplicated(keep=False)].copy()

    outlier_summary, outlier_data = get_outlier_data(df)

    total_missing = int(df.isna().sum().sum())
    total_duplicate = int(df.duplicated().sum())

    total_outlier = (
        int(outlier_summary["Jumlah Outlier"].sum())
        if not outlier_summary.empty else 0
    )

    findings_df = buat_ringkasan_temuan(df)

else:
    total_rows = 0
    total_columns = 0
    total_missing = 0
    total_duplicate = 0
    total_outlier = 0

    missing_data = pd.DataFrame()
    duplicate_data = pd.DataFrame()
    outlier_summary = pd.DataFrame()
    outlier_data = pd.DataFrame()
    findings_df = pd.DataFrame()


# =====================================================
# 7. HALAMAN DASHBOARD
# =====================================================

if menu == "Dashboard":

    st.markdown("""
    <div class="hero">
        <div class="brand-logo" style="margin:0 0 20px 0;">AW</div>
        <h1>Selamat Datang di ADIWIA</h1>
        <p>
            Asisten Digital Audit Widianti & Adinda merupakan aplikasi
            berbasis Artificial Intelligence (AI) yang dirancang untuk
            membantu proses pemeriksaan, analisis, dan evaluasi data
            keuangan secara lebih praktis dan sistematis.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## Tentang ADIWIA")

    st.write("""
    ADIWIA dikembangkan sebagai alat bantu digital dalam proses audit.
    Aplikasi ini membantu pengguna mengidentifikasi potensi kesalahan
    data, memeriksa transaksi keuangan, membandingkan anggaran dengan
    realisasi, serta menghasilkan analisis awal menggunakan teknologi AI.

    Hasil pemeriksaan aplikasi merupakan indikasi awal yang tetap perlu
    ditinjau dan diverifikasi oleh auditor.
    """)

    st.markdown("## Fitur Utama")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="section-card">
            <h4>📂 Upload Data Audit</h4>
            <p>
                Mengunggah data transaksi dalam format Excel atau CSV
                sebagai bahan pemeriksaan audit.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class="section-card">
            <h4>🔍 Pemeriksaan Data Audit</h4>
            <p>
                Membantu memeriksa data kosong, data duplikat,
                outlier, serta keseimbangan debit dan kredit.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="section-card">
            <h4>📊 Analisis Keuangan</h4>
            <p>
                Membandingkan nilai anggaran dan realisasi untuk
                melihat selisih serta potensi kelebihan anggaran.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class="section-card">
            <h4>🤖 AI Audit Analysis</h4>
            <p>
                Memanfaatkan AI untuk membantu memberikan analisis
                awal berdasarkan data dan hasil pemeriksaan.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("## Alur Penggunaan ADIWIA")

    step1, step2, step3 = st.columns(3)

    with step1:
        st.markdown("""
        <div class="section-card">
            <h4>01. Upload</h4>
            <p>Unggah file data keuangan yang akan diperiksa.</p>
        </div>
        """, unsafe_allow_html=True)

    with step2:
        st.markdown("""
        <div class="section-card">
            <h4>02. Pemeriksaan</h4>
            <p>Lakukan pemeriksaan data dan analisis keuangan.</p>
        </div>
        """, unsafe_allow_html=True)

    with step3:
        st.markdown("""
        <div class="section-card">
            <h4>03. Laporan</h4>
            <p>Tinjau hasil temuan dan unduh laporan audit.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## Aktivitas Data Audit")

    if df is not None:

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Jumlah Transaksi", f"{total_rows:,}")

        with c2:
            st.metric("Jumlah Kolom", f"{total_columns:,}")

        with c3:
            st.metric("Data Kosong", f"{total_missing:,}")

        with c4:
            st.metric("Data Duplikat", f"{total_duplicate:,}")

        st.success(f"File aktif: {st.session_state.file_name}")

    else:
        st.info(
            "Belum ada data audit yang diunggah. "
            "Silakan pilih menu Upload Data Audit untuk memulai."
        )


# =====================================================
# 8. UPLOAD DATA AUDIT
# =====================================================

elif menu == "Upload Data Audit":

    st.markdown('<p class="main-title">Upload Data Audit</p>',
                unsafe_allow_html=True)

    st.write(
        "Unggah file transaksi keuangan yang akan digunakan "
        "dalam proses pemeriksaan dan analisis audit."
    )

    uploaded_file = st.file_uploader(
        "Pilih file Excel atau CSV",
        type=["xlsx", "xls", "csv"]
    )

    if uploaded_file is not None:

        try:
            if uploaded_file.name.endswith(".csv"):
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file)

            st.session_state.audit_df = uploaded_df
            st.session_state.file_name = uploaded_file.name
            st.session_state.ai_result = None

            st.session_state.debit_choice = None
            st.session_state.credit_choice = None
            st.session_state.budget_choice = None
            st.session_state.actual_choice = None

            st.success("Data berhasil diunggah!")

            st.markdown("### Preview Data")

            st.dataframe(
                uploaded_df.head(10),
                use_container_width=True
            )

            col1, col2, col3 = st.columns(3)

            col1.metric("Jumlah Baris", len(uploaded_df))
            col2.metric("Jumlah Kolom", len(uploaded_df.columns))
            col3.metric("Data Kosong", int(uploaded_df.isna().sum().sum()))

        except Exception as error:
            st.error(f"Gagal membaca file: {error}")

    if st.session_state.audit_df is not None:

        st.markdown("---")
        st.markdown("### Data yang Sedang Digunakan")

        st.write(f"Nama file: **{st.session_state.file_name}**")

        if st.button("Hapus Data yang Diunggah", type="secondary"):

            st.session_state.audit_df = None
            st.session_state.file_name = ""
            st.session_state.ai_result = None

            st.session_state.debit_choice = None
            st.session_state.credit_choice = None
            st.session_state.budget_choice = None
            st.session_state.actual_choice = None

            st.rerun()


# =====================================================
# 9. INFORMASI DATA
# =====================================================

elif menu == "Informasi Data":

    st.markdown('<p class="main-title">Informasi Data</p>',
                unsafe_allow_html=True)

    if df is None:
        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        st.success(f"Data aktif: {st.session_state.file_name}")

        col1, col2, col3 = st.columns(3)

        col1.metric("Jumlah Baris", total_rows)
        col2.metric("Jumlah Kolom", total_columns)
        col3.metric("Jumlah Data Kosong", total_missing)

        st.markdown("### Preview Dataset")

        st.dataframe(df.head(20), use_container_width=True)

        st.markdown("### Struktur Kolom")

        column_info = pd.DataFrame({
            "Nama Kolom": df.columns,
            "Tipe Data": df.dtypes.astype(str).values,
            "Jumlah Data Terisi": df.notna().sum().values,
            "Jumlah Data Kosong": df.isna().sum().values
        })

        st.dataframe(column_info, use_container_width=True)

        st.markdown("### Statistik Deskriptif")

        st.dataframe(
            df.describe(include="all").transpose(),
            use_container_width=True
        )


# =====================================================
# 10. PEMERIKSAAN DATA AUDIT
# =====================================================

elif menu == "Pemeriksaan Data Audit":

    st.markdown('<p class="main-title">Pemeriksaan Data Audit</p>',
                unsafe_allow_html=True)

    if df is None:
        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        st.write(
            "Pemeriksaan dilakukan untuk membantu mengidentifikasi "
            "indikasi ketidakwajaran dan masalah dalam dataset."
        )

        st.markdown("### 1. Pemeriksaan Data Kosong")

        if missing_data.empty:
            st.success("Tidak ditemukan data kosong.")
        else:
            st.warning("Ditemukan data kosong pada beberapa kolom.")
            st.dataframe(missing_data, use_container_width=True)

        st.markdown("### 2. Pemeriksaan Data Duplikat")

        if duplicate_data.empty:
            st.success("Tidak ditemukan baris data duplikat.")
        else:
            st.warning(f"Ditemukan {total_duplicate} baris duplikat.")
            st.dataframe(duplicate_data, use_container_width=True)

        st.markdown("### 3. Pemeriksaan Data Outlier")

        if outlier_summary.empty:
            st.success("Tidak ditemukan outlier berdasarkan metode IQR.")
        else:
            st.warning(
                f"Ditemukan {total_outlier} indikasi nilai outlier."
            )

            st.dataframe(
                outlier_summary,
                use_container_width=True
            )

            with st.expander("Lihat Data Outlier"):
                st.dataframe(outlier_data, use_container_width=True)

        st.markdown("### 4. Pemeriksaan Debit dan Kredit")

        numeric_columns = get_numeric_columns(df)

        if len(numeric_columns) < 2:
            st.info(
                "Diperlukan minimal dua kolom numerik "
                "untuk melakukan pemeriksaan debit dan kredit."
            )

        else:

            debit_col = st.selectbox(
                "Pilih Kolom Debit",
                ["-- Pilih Kolom --"] + numeric_columns,
                key="debit_select"
            )

            credit_col = st.selectbox(
                "Pilih Kolom Kredit",
                ["-- Pilih Kolom --"] + numeric_columns,
                key="credit_select"
            )

            if (
                debit_col != "-- Pilih Kolom --"
                and credit_col != "-- Pilih Kolom --"
            ):

                if debit_col == credit_col:
                    st.error("Kolom debit dan kredit harus berbeda.")

                else:

                    st.session_state.debit_choice = debit_col
                    st.session_state.credit_choice = credit_col

                    total_debit = pd.to_numeric(
                        df[debit_col], errors="coerce"
                    ).fillna(0).sum()

                    total_credit = pd.to_numeric(
                        df[credit_col], errors="coerce"
                    ).fillna(0).sum()

                    selisih = abs(total_debit - total_credit)

                    a, b, c = st.columns(3)

                    a.metric("Total Debit", format_rupiah(total_debit))
                    b.metric("Total Kredit", format_rupiah(total_credit))
                    c.metric("Selisih", format_rupiah(selisih))

                    if selisih <= 0.01:
                        st.success(
                            "Total debit dan kredit seimbang."
                        )
                    else:
                        st.warning(
                            "Total debit dan kredit belum seimbang."
                        )

                    st.caption(
                        "Catatan: Pemeriksaan ini membandingkan total "
                        "kolom debit dan kredit, bukan memvalidasi "
                        "keseimbangan setiap jurnal secara individual."
                    )


# =====================================================
# 11. ANALISIS ANGGARAN DAN REALISASI
# =====================================================

elif menu == "Analisis Anggaran dan Realisasi":

    st.markdown(
        '<p class="main-title">Analisis Anggaran dan Realisasi</p>',
        unsafe_allow_html=True
    )

    if df is None:
        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        numeric_columns = get_numeric_columns(df)

        if len(numeric_columns) < 2:
            st.warning(
                "Data harus memiliki minimal dua kolom numerik "
                "untuk melakukan analisis."
            )

        else:

            st.write(
                "Pilih kolom anggaran dan realisasi yang ingin "
                "dibandingkan."
            )

            budget_col = st.selectbox(
                "Pilih Kolom Anggaran",
                ["-- Pilih Kolom --"] + numeric_columns,
                key="budget_select"
            )

            actual_col = st.selectbox(
                "Pilih Kolom Realisasi",
                ["-- Pilih Kolom --"] + numeric_columns,
                key="actual_select"
            )

            if (
                budget_col != "-- Pilih Kolom --"
                and actual_col != "-- Pilih Kolom --"
            ):

                if budget_col == actual_col:
                    st.error(
                        "Kolom anggaran dan realisasi harus berbeda."
                    )

                else:

                    st.session_state.budget_choice = budget_col
                    st.session_state.actual_choice = actual_col

                    analysis_df = pd.DataFrame()

                    analysis_df["Anggaran"] = pd.to_numeric(
                        df[budget_col], errors="coerce"
                    )

                    analysis_df["Realisasi"] = pd.to_numeric(
                        df[actual_col], errors="coerce"
                    )

                    analysis_df = analysis_df.fillna(0)

                    analysis_df["Selisih"] = (
                        analysis_df["Realisasi"] -
                        analysis_df["Anggaran"]
                    )

                    analysis_df["Persentase Realisasi"] = (
                        analysis_df["Realisasi"]
                        .div(analysis_df["Anggaran"].replace(0, pd.NA))
                        .mul(100)
                    )

                    total_anggaran = analysis_df["Anggaran"].sum()
                    total_realisasi = analysis_df["Realisasi"].sum()
                    total_selisih = total_realisasi - total_anggaran

                    if total_anggaran != 0:
                        persentase_total = (
                            total_realisasi / total_anggaran
                        ) * 100
                    else:
                        persentase_total = 0

                    c1, c2, c3 = st.columns(3)

                    c1.metric(
                        "Total Anggaran",
                        format_rupiah(total_anggaran)
                    )

                    c2.metric(
                        "Total Realisasi",
                        format_rupiah(total_realisasi)
                    )

                    c3.metric(
                        "Selisih",
                        format_rupiah(total_selisih)
                    )

                    st.metric(
                        "Persentase Realisasi",
                        f"{persentase_total:,.2f}%"
                    )

                    st.markdown("### Grafik Anggaran dan Realisasi")

                    chart_df = pd.DataFrame({
                        "Jenis": ["Anggaran", "Realisasi"],
                        "Jumlah": [
                            total_anggaran,
                            total_realisasi
                        ]
                    })

                    fig = px.bar(
                        chart_df,
                        x="Jenis",
                        y="Jumlah",
                        text_auto=".2s",
                        title="Perbandingan Total Anggaran dan Realisasi"
                    )

                    fig.update_layout(
                        plot_bgcolor="white",
                        paper_bgcolor="white"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

                    st.markdown("### Rincian Perbandingan")

                    st.dataframe(
                        analysis_df,
                        use_container_width=True
                    )

                    if total_selisih > 0:
                        st.warning(
                            "Total realisasi lebih besar daripada anggaran."
                        )
                    elif total_selisih < 0:
                        st.info(
                            "Total realisasi masih berada di bawah anggaran."
                        )
                    else:
                        st.success(
                            "Total realisasi sama dengan anggaran."
                        )


# =====================================================
# 12. RINGKASAN TEMUAN AUDIT
# =====================================================

elif menu == "Ringkasan Temuan Audit":

    st.markdown(
        '<p class="main-title">Ringkasan Temuan Audit</p>',
        unsafe_allow_html=True
    )

    if df is None:
        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        st.write(
            "Halaman ini menampilkan rangkuman hasil pemeriksaan "
            "otomatis berdasarkan data yang telah diunggah."
        )

        c1, c2, c3 = st.columns(3)

        c1.metric("Data Kosong", total_missing)
        c2.metric("Data Duplikat", total_duplicate)
        c3.metric("Data Outlier", total_outlier)

        st.markdown("### Daftar Temuan")

        st.dataframe(
            findings_df,
            use_container_width=True
        )

        st.caption(
            "Temuan yang ditampilkan merupakan hasil pemeriksaan "
            "otomatis dan bukan kesimpulan audit final. "
            "Auditor tetap perlu melakukan verifikasi lebih lanjut."
        )


# =====================================================
# 13. AI AUDIT ANALYSIS
# =====================================================

elif menu == "AI Audit Analysis":

    st.markdown(
        '<p class="main-title">AI Audit Analysis</p>',
        unsafe_allow_html=True
    )

    if df is None:
        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        st.write("""
        Fitur ini menggunakan Artificial Intelligence untuk membantu
        memberikan analisis awal berdasarkan struktur data, statistik,
        dan hasil pemeriksaan audit.
        """)

        st.info(
            "AI membantu memberikan analisis awal. "
            "Hasilnya tetap perlu diperiksa dan diverifikasi oleh auditor."
        )

        if st.button("Mulai Analisis AI", type="primary"):

            with st.spinner("ADIWIA sedang menganalisis data..."):

                preview = df.head(100).to_string(index=False)

                statistics = df.describe(
                    include="all"
                ).transpose().to_string()

                findings_text = findings_df.to_string(index=False)

                prompt = f"""
Anda adalah asisten digital audit yang membantu pemeriksaan data keuangan.

Lakukan analisis awal terhadap dataset berikut.

NAMA FILE:
{st.session_state.file_name}

JUMLAH BARIS:
{len(df)}

JUMLAH KOLOM:
{len(df.columns)}

NAMA KOLOM:
{list(df.columns)}

PREVIEW DATA (maksimal 100 baris):
{preview}

STATISTIK DATA:
{statistics}

RINGKASAN TEMUAN OTOMATIS:
{findings_text}

Buat analisis dalam bahasa Indonesia dengan susunan:

1. Gambaran Umum Data
2. Hasil Pemeriksaan Data
3. Potensi Risiko atau Ketidakwajaran
4. Analisis dan Interpretasi
5. Rekomendasi Tindak Lanjut Audit

Gunakan bahasa yang jelas, objektif, dan mudah dipahami.
Jangan mengarang fakta yang tidak terdapat dalam dataset.
Bedakan antara indikasi dan temuan yang sudah terbukti.
Jelaskan keterbatasan analisis jika data tidak mencukupi.
"""

                st.session_state.ai_result = ask_gemini(prompt)

        if st.session_state.ai_result:

            st.markdown("---")
            st.markdown("### Hasil Analisis ADIWIA")

            st.markdown(st.session_state.ai_result)


# =====================================================
# 14. DOWNLOAD LAPORAN AUDIT
# =====================================================

elif menu == "Download Laporan Audit":

    st.markdown(
        '<p class="main-title">Download Laporan Audit</p>',
        unsafe_allow_html=True
    )

    if df is None:
        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        st.write(
            "Unduh hasil pemeriksaan dan analisis audit "
            "dalam satu file Excel."
        )

        st.markdown("### Isi Laporan")

        st.write("""
        Laporan Excel berisi:
        - Data Transaksi
        - Informasi Data
        - Data Kosong
        - Data Duplikat
        - Data Outlier
        - Pemeriksaan Debit Kredit
        - Analisis Anggaran dan Realisasi
        - Ringkasan Temuan Audit
        - Analisis AI
        """)

        if st.button("Siapkan Laporan Audit", type="primary"):

            output = BytesIO()

            with pd.ExcelWriter(
                output,
                engine="openpyxl"
            ) as writer:

                # Data transaksi
                df.to_excel(
                    writer,
                    sheet_name="Data Transaksi",
                    index=False
                )

                # Informasi data
                column_info = pd.DataFrame({
                    "Nama Kolom": df.columns,
                    "Tipe Data": df.dtypes.astype(str).values,
                    "Jumlah Data Terisi": df.notna().sum().values,
                    "Jumlah Data Kosong": df.isna().sum().values
                })

                column_info.to_excel(
                    writer,
                    sheet_name="Informasi Data",
                    index=False
                )

                # Data kosong
                if missing_data.empty:
                    missing_data_export = pd.DataFrame({
                        "Keterangan": ["Tidak ditemukan data kosong."]
                    })
                else:
                    missing_data_export = missing_data

                missing_data_export.to_excel(
                    writer,
                    sheet_name="Data Kosong",
                    index=False
                )

                # Data duplikat
                if duplicate_data.empty:
                    duplicate_export = pd.DataFrame({
                        "Keterangan": ["Tidak ditemukan data duplikat."]
                    })
                else:
                    duplicate_export = duplicate_data

                duplicate_export.to_excel(
                    writer,
                    sheet_name="Data Duplikat",
                    index=False
                )

                # Data outlier
                if outlier_data.empty:
                    outlier_export = pd.DataFrame({
                        "Keterangan": ["Tidak ditemukan data outlier."]
                    })
                else:
                    outlier_export = outlier_data

                outlier_export.to_excel(
                    writer,
                    sheet_name="Data Outlier",
                    index=False
                )

                # Pemeriksaan debit kredit
                debit_col = st.session_state.debit_choice
                credit_col = st.session_state.credit_choice

                if (
                    debit_col in df.columns
                    and credit_col in df.columns
                    and debit_col != credit_col
                ):

                    debit_total = pd.to_numeric(
                        df[debit_col], errors="coerce"
                    ).fillna(0).sum()

                    credit_total = pd.to_numeric(
                        df[credit_col], errors="coerce"
                    ).fillna(0).sum()

                    debit_credit_df = pd.DataFrame({
                        "Keterangan": [
                            "Total Debit",
                            "Total Kredit",
                            "Selisih"
                        ],
                        "Nilai": [
                            debit_total,
                            credit_total,
                            abs(debit_total - credit_total)
                        ]
                    })

                else:
                    debit_credit_df = pd.DataFrame({
                        "Keterangan": [
                            "Pemeriksaan debit dan kredit belum dilakukan."
                        ]
                    })

                debit_credit_df.to_excel(
                    writer,
                    sheet_name="Debit Kredit",
                    index=False
                )

                # Analisis anggaran dan realisasi
                budget_col = st.session_state.budget_choice
                actual_col = st.session_state.actual_choice

                if (
                    budget_col in df.columns
                    and actual_col in df.columns
                    and budget_col != actual_col
                ):

                    budget_actual_df = pd.DataFrame()

                    budget_actual_df["Anggaran"] = pd.to_numeric(
                        df[budget_col], errors="coerce"
                    )

                    budget_actual_df["Realisasi"] = pd.to_numeric(
                        df[actual_col], errors="coerce"
                    )

                    budget_actual_df = budget_actual_df.fillna(0)

                    budget_actual_df["Selisih"] = (
                        budget_actual_df["Realisasi"] -
                        budget_actual_df["Anggaran"]
                    )

                    budget_actual_df.to_excel(
                        writer,
                        sheet_name="Anggaran Realisasi",
                        index=False
                    )

                else:
                    pd.DataFrame({
                        "Keterangan": [
                            "Analisis anggaran dan realisasi belum dilakukan."
                        ]
                    }).to_excel(
                        writer,
                        sheet_name="Anggaran Realisasi",
                        index=False
                    )

                # Ringkasan temuan
                findings_df.to_excel(
                    writer,
                    sheet_name="Ringkasan Temuan",
                    index=False
                )

                # Analisis AI
                ai_export = pd.DataFrame({
                    "Hasil Analisis AI": [
                        st.session_state.ai_result
                        if st.session_state.ai_result
                        else "Analisis AI belum dilakukan."
                    ]
                })

                ai_export.to_excel(
                    writer,
                    sheet_name="Analisis AI",
                    index=False
                )

            output.seek(0)

            st.success("Laporan audit berhasil disiapkan!")

            st.download_button(
                label="📥 Download Laporan Audit Excel",
                data=output.getvalue(),
                file_name="Laporan_Audit_ADIWIA.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                type="primary"
            )


# =====================================================
# 15. FOOTER
# =====================================================

st.markdown("""
<div class="footer">
    ADIWIA - Asisten Digital Audit Widianti & Adinda<br>
    Digital Audit Assistant | Artificial Intelligence
</div>
""", unsafe_allow_html=True)

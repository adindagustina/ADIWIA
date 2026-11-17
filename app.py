
import os
import time
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from google import genai


# =========================================================
# 1. KONFIGURASI
# =========================================================

st.set_page_config(
    page_title="ADIWIA | Digital Audit Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

api_key = os.getenv("GEMINI_API_KEY")

try:
    if not api_key:
        api_key = st.secrets.get("GEMINI_API_KEY")
except Exception:
    pass

client = genai.Client(api_key=api_key) if api_key else None


# =========================================================
# 2. DESAIN APLIKASI
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #F5F7FB;
}

[data-testid="stSidebar"] {
    background-color: #14243D;
}

[data-testid="stSidebar"] * {
    color: #FFFFFF;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    padding: 7px 10px;
    border-radius: 8px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background-color: #294365;
}

.main-header {
    background: linear-gradient(120deg, #14243D, #294365);
    padding: 25px;
    border-radius: 15px;
    color: white;
    margin-bottom: 25px;
}

.brand-logo {
    width: 62px;
    height: 62px;
    border-radius: 15px;
    background: linear-gradient(135deg, #D6B66D, #F4DFA5);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #14243D;
    font-size: 36px;
    font-family: Georgia, serif;
    font-weight: bold;
}

.brand-name {
    font-size: 29px;
    font-weight: 800;
    letter-spacing: 3px;
    margin: 0;
}

.brand-subtitle {
    color: #D8DFE9;
    font-size: 12px;
    margin-top: 4px;
}

.page-title {
    color: #172B49;
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 3px;
}

.page-description {
    color: #718096;
    font-size: 14px;
    margin-bottom: 22px;
}

div[data-testid="stMetric"] {
    background-color: #FFFFFF;
    padding: 17px;
    border: 1px solid #E5E9F0;
    border-radius: 12px;
    box-shadow: 0 2px 7px rgba(0,0,0,0.03);
}

.stDownloadButton button {
    background-color: #172B49;
    color: white;
    border: none;
    border-radius: 9px;
}

.stDownloadButton button:hover {
    background-color: #294365;
    color: white;
}

div.stButton > button {
    border-radius: 9px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# 3. SESSION STATE
# =========================================================

if "audit_df" not in st.session_state:
    st.session_state.audit_df = None

if "ai_result" not in st.session_state:
    st.session_state.ai_result = None

if "debit_choice" not in st.session_state:
    st.session_state.debit_choice = "-- Pilih Kolom --"

if "credit_choice" not in st.session_state:
    st.session_state.credit_choice = "-- Pilih Kolom --"

if "budget_choice" not in st.session_state:
    st.session_state.budget_choice = "-- Pilih Kolom --"

if "actual_choice" not in st.session_state:
    st.session_state.actual_choice = "-- Pilih Kolom --"


# =========================================================
# 4. FUNGSI PENDUKUNG
# =========================================================

def format_rupiah(value):
    return "Rp {:,.2f}".format(float(value))


def ask_gemini(prompt, retries=3):

    if client is None:
        return (
            "API Key Gemini belum diatur. "
            "Silakan masukkan GEMINI_API_KEY pada Streamlit Secrets."
        )

    for attempt in range(retries):

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            return response.text or "AI tidak menghasilkan jawaban."

        except Exception as e:

            error_message = str(e).upper()

            temporary_error = any(
                code in error_message
                for code in ["503", "429", "500", "504", "UNAVAILABLE"]
            )

            if temporary_error and attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue

            return f"Analisis AI belum berhasil. Keterangan: {e}"

    return "Analisis AI gagal setelah beberapa percobaan."


def get_outlier_data(data):

    numeric_columns = data.select_dtypes(
        include="number"
    ).columns

    outlier_indices = set()

    for column in numeric_columns:

        series = data[column].dropna()

        if len(series) < 4:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower = q1 - (1.5 * iqr)
        upper = q3 + (1.5 * iqr)

        detected = series[
            (series < lower) | (series > upper)
        ]

        outlier_indices.update(detected.index.tolist())

    result = data.loc[sorted(outlier_indices)].copy()

    return result


# =========================================================
# 5. SIDEBAR DAN NAVIGASI
# =========================================================

with st.sidebar:

    st.markdown("""
    <div style="text-align:center; padding:18px 5px;">
        <div class="brand-logo" style="margin:auto;">A</div>
        <h2 style="color:white; margin:10px 0 0 0;">
            ADIWIA
        </h2>
        <p style="font-size:11px;color:#D8DFE9;">
            Asisten Digital Audit<br>
            Widianti & Adinda
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.caption("MENU UTAMA")

    menu = st.radio(
        "Navigasi",
        [
            "Dashboard",
            "Upload Data Audit",
            "Informasi Data",
            "Pemeriksaan Data Audit",
            "Analisis Anggaran",
            "Ringkasan Temuan Audit",
            "AI Audit Analysis",
            "Download Laporan"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    if st.session_state.audit_df is not None:
        st.success("Data audit tersedia")
    else:
        st.info("Belum ada data audit")

    st.markdown("""
    <div style="text-align:center; padding-top:20px;">
        <small style="color:#B9C5D5;">
            ADIWIA DIGITAL AUDIT<br>
            Version 1.0 | 2026
        </small>
    </div>
    """, unsafe_allow_html=True)


# =========================================================
# 6. MEMBACA DATA DAN MENYIAPKAN PEMERIKSAAN
# =========================================================

df = st.session_state.audit_df

if df is not None:

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    missing_data = []

    for column, count in df.isna().sum().items():

        if count > 0:
            missing_data.append({
                "Kolom": column,
                "Jumlah Data Kosong": int(count)
            })

    missing_df = pd.DataFrame(
        missing_data,
        columns=["Kolom", "Jumlah Data Kosong"]
    )

    total_missing = int(df.isna().sum().sum())

    duplicate_rows = df[
        df.duplicated(keep=False)
    ].copy()

    total_duplicate = int(df.duplicated().sum())

    outlier_rows = get_outlier_data(df)

    total_outlier = len(outlier_rows)

    # Pemeriksaan debit kredit berdasarkan pilihan pengguna
    debit_total = None
    credit_total = None
    debit_credit_report = pd.DataFrame()

    debit_choice = st.session_state.debit_choice
    credit_choice = st.session_state.credit_choice

    if (
        debit_choice in numeric_columns
        and credit_choice in numeric_columns
        and debit_choice != credit_choice
    ):

        debit_total = pd.to_numeric(
            df[debit_choice],
            errors="coerce"
        ).sum()

        credit_total = pd.to_numeric(
            df[credit_choice],
            errors="coerce"
        ).sum()

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

    # Pemeriksaan anggaran dan realisasi
    budget_df = pd.DataFrame()
    budget_total = None
    actual_total = None

    budget_choice = st.session_state.budget_choice
    actual_choice = st.session_state.actual_choice

    if (
        budget_choice in numeric_columns
        and actual_choice in numeric_columns
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

        budget_df = pd.DataFrame({
            "Nomor Baris": range(1, len(df) + 1),
            "Anggaran": budget_values,
            "Realisasi": actual_values
        })

        budget_df["Selisih"] = (
            budget_df["Realisasi"] -
            budget_df["Anggaran"]
        )

        budget_df["Persentase Realisasi"] = (
            budget_df["Realisasi"] /
            budget_df["Anggaran"].where(
                budget_df["Anggaran"] != 0
            )
        ) * 100

        budget_df["Keterangan"] = "Sesuai Anggaran"

        budget_df.loc[
            budget_df["Realisasi"] > budget_df["Anggaran"],
            "Keterangan"
        ] = "Melebihi Anggaran"

        budget_df.loc[
            budget_df["Anggaran"].isna() |
            budget_df["Realisasi"].isna(),
            "Keterangan"
        ] = "Data Tidak Lengkap"

        budget_total = budget_values.sum()
        actual_total = actual_values.sum()

    # Menggabungkan seluruh temuan
    findings = []

    for item in missing_data:

        findings.append({
            "Jenis Temuan": "Data Kosong",
            "Keterangan": (
                f"Kolom {item['Kolom']} memiliki "
                f"{item['Jumlah Data Kosong']} data kosong."
            ),
            "Jumlah": item["Jumlah Data Kosong"]
        })

    if total_duplicate > 0:

        findings.append({
            "Jenis Temuan": "Data Duplikat",
            "Keterangan": (
                f"Ditemukan {total_duplicate} baris duplikat "
                "berdasarkan seluruh kolom."
            ),
            "Jumlah": total_duplicate
        })

    if total_outlier > 0:

        findings.append({
            "Jenis Temuan": "Outlier",
            "Keterangan": (
                f"Ditemukan {total_outlier} baris yang "
                "terindikasi memiliki nilai outlier."
            ),
            "Jumlah": total_outlier
        })

    if debit_total is not None and credit_total is not None:

        difference = debit_total - credit_total

        if abs(difference) >= 0.01:

            findings.append({
                "Jenis Temuan": "Debit dan Kredit",
                "Keterangan": (
                    "Total debit dan kredit tidak seimbang. "
                    f"Selisih {format_rupiah(abs(difference))}."
                ),
                "Jumlah": 1
            })

    if budget_total is not None and actual_total is not None:

        if actual_total > budget_total:

            findings.append({
                "Jenis Temuan": "Anggaran dan Realisasi",
                "Keterangan": (
                    "Total realisasi melebihi total anggaran "
                    f"sebesar {format_rupiah(actual_total - budget_total)}."
                ),
                "Jumlah": 1
            })

        over_budget_count = int(
            budget_df["Keterangan"].eq("Melebihi Anggaran").sum()
        )

        if over_budget_count > 0:

            findings.append({
                "Jenis Temuan": "Realisasi per Baris",
                "Keterangan": (
                    f"Terdapat {over_budget_count} baris "
                    "realisasi yang melebihi anggaran."
                ),
                "Jumlah": over_budget_count
            })

    findings_df = pd.DataFrame(
        findings,
        columns=["Jenis Temuan", "Keterangan", "Jumlah"]
    )

    # Informasi tipe data
    type_df = pd.DataFrame({
        "Nama Kolom": df.columns,
        "Tipe Data": df.dtypes.astype(str).values
    })

else:

    numeric_columns = []
    missing_data = []
    missing_df = pd.DataFrame()
    duplicate_rows = pd.DataFrame()
    outlier_rows = pd.DataFrame()
    findings_df = pd.DataFrame()
    budget_df = pd.DataFrame()
    debit_credit_report = pd.DataFrame()


# =========================================================
# 7. HALAMAN DASHBOARD
# =========================================================

if menu == "Dashboard":

    st.markdown(
        '<div class="page-title">Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="page-description">'
        'Selamat datang di ADIWIA. Pantau ringkasan pemeriksaan '
        'data keuangan dalam satu halaman.'
        '</div>',
        unsafe_allow_html=True
    )

    if df is None:

        st.info(
            "Belum ada data audit. Silakan buka menu Upload Data Audit "
            "untuk memulai pemeriksaan."
        )

    else:

        st.subheader("Ringkasan Data Audit")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Total Transaksi", f"{len(df):,}")
        c2.metric("Data Kosong", f"{total_missing:,}")
        c3.metric("Data Duplikat", f"{total_duplicate:,}")
        c4.metric("Data Outlier", f"{total_outlier:,}")

        st.divider()

        left, right = st.columns([1.5, 1])

        with left:

            st.subheader("Grafik Temuan Pemeriksaan")

            chart_data = pd.DataFrame({
                "Jenis Pemeriksaan": [
                    "Data Kosong",
                    "Data Duplikat",
                    "Data Outlier"
                ],
                "Jumlah": [
                    total_missing,
                    total_duplicate,
                    total_outlier
                ]
            })

            fig = px.bar(
                chart_data,
                x="Jenis Pemeriksaan",
                y="Jumlah",
                color="Jenis Pemeriksaan",
                text="Jumlah",
                color_discrete_sequence=[
                    "#243B5A",
                    "#C5A45D",
                    "#7186A5"
                ]
            )

            fig.update_layout(
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
                xaxis_title="",
                yaxis_title="Jumlah Temuan"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        with right:

            st.subheader("Status Pemeriksaan")

            if len(findings_df) > 0:

                st.warning(
                    f"Terdapat {len(findings_df)} kategori temuan "
                    "yang memerlukan pemeriksaan lebih lanjut."
                )

            else:

                st.success(
                    "Belum ditemukan indikasi temuan dari pemeriksaan "
                    "yang telah dilakukan."
                )

            st.write("**Jumlah Kolom:**", len(df.columns))
            st.write("**Kolom Numerik:**", len(numeric_columns))
            st.write("**Total Temuan:**", len(findings_df))

        st.divider()

        st.subheader("Pratinjau Data Transaksi")

        st.dataframe(
            df.head(10),
            use_container_width=True
        )


# =========================================================
# 8. HALAMAN UPLOAD DATA
# =========================================================

elif menu == "Upload Data Audit":

    st.markdown(
        '<div class="page-title">Upload Data Audit</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="page-description">'
        'Unggah file transaksi keuangan untuk memulai pemeriksaan.'
        '</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Pilih file Excel",
        type=["xlsx"],
        help="Gunakan file Excel dengan format .xlsx"
    )

    if uploaded_file is not None:

        try:

            new_df = pd.read_excel(uploaded_file)
            new_df.columns = (
                new_df.columns.astype(str).str.strip()
            )

            if new_df.empty:
                st.error("File Excel tidak memiliki data.")
            else:

                st.session_state.audit_df = new_df

                # Reset pilihan kolom ketika data diganti
                st.session_state.debit_choice = "-- Pilih Kolom --"
                st.session_state.credit_choice = "-- Pilih Kolom --"
                st.session_state.budget_choice = "-- Pilih Kolom --"
                st.session_state.actual_choice = "-- Pilih Kolom --"
                st.session_state.ai_result = None

                st.success(
                    f"Data berhasil diunggah! "
                    f"Jumlah {len(new_df)} baris."
                )

                st.dataframe(
                    new_df.head(15),
                    use_container_width=True
                )

        except Exception as e:

            st.error(f"Gagal membaca file: {e}")

    if st.session_state.audit_df is not None:

        st.success("File audit sudah tersedia di aplikasi.")

        st.write(
            f"Total transaksi: "
            f"{len(st.session_state.audit_df):,}"
        )


# =========================================================
# 9. HALAMAN INFORMASI DATA
# =========================================================

elif menu == "Informasi Data":

    st.markdown(
        '<div class="page-title">Informasi Data</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="page-description">'
        'Informasi struktur dan isi data transaksi yang diunggah.'
        '</div>',
        unsafe_allow_html=True
    )

    if df is None:

        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        c1, c2, c3 = st.columns(3)

        c1.metric("Jumlah Baris", len(df))
        c2.metric("Jumlah Kolom", len(df.columns))
        c3.metric("Kolom Numerik", len(numeric_columns))

        st.subheader("Struktur Kolom")

        st.dataframe(
            type_df,
            use_container_width=True
        )

        st.subheader("Pratinjau Data")

        st.dataframe(
            df,
            use_container_width=True
        )

        st.subheader("Statistik Deskriptif")

        if numeric_columns:

            st.dataframe(
                df[numeric_columns].describe().T,
                use_container_width=True
            )

        else:

            st.info("Tidak terdapat kolom numerik.")


# =========================================================
# 10. HALAMAN PEMERIKSAAN DATA AUDIT
# =========================================================

elif menu == "Pemeriksaan Data Audit":

    st.markdown(
        '<div class="page-title">Pemeriksaan Data Audit</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="page-description">'
        'Periksa kelengkapan, duplikasi, nilai tidak wajar, '
        'serta keseimbangan debit dan kredit.'
        '</div>',
        unsafe_allow_html=True
    )

    if df is None:

        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        st.subheader("A. Pemeriksaan Data Kosong")

        if not missing_df.empty:

            st.warning("Ditemukan data kosong.")

            st.dataframe(
                missing_df,
                use_container_width=True
            )

        else:

            st.success("Tidak ditemukan data kosong.")

        st.divider()

        st.subheader("B. Pemeriksaan Data Duplikat")

        if not duplicate_rows.empty:

            st.warning(
                f"Ditemukan {total_duplicate} baris duplikat "
                "tambahan."
            )

            st.dataframe(
                duplicate_rows,
                use_container_width=True
            )

        else:

            st.success("Tidak ditemukan baris duplikat.")

        st.divider()

        st.subheader("C. Pemeriksaan Outlier")

        if not outlier_rows.empty:

            st.warning(
                f"Ditemukan {total_outlier} baris yang "
                "terindikasi outlier."
            )

            st.dataframe(
                outlier_rows,
                use_container_width=True
            )

        else:

            st.success(
                "Tidak ditemukan indikasi outlier berdasarkan IQR."
            )

        st.caption(
            "Outlier merupakan indikasi statistik dan perlu "
            "diverifikasi berdasarkan konteks transaksi."
        )

        st.divider()

        st.subheader("D. Pemeriksaan Debit dan Kredit")

        if len(numeric_columns) >= 2:

            debit_options = ["-- Pilih Kolom --"] + numeric_columns

            if st.session_state.debit_choice not in debit_options:
                st.session_state.debit_choice = "-- Pilih Kolom --"

            if st.session_state.credit_choice not in debit_options:
                st.session_state.credit_choice = "-- Pilih Kolom --"

            col1, col2 = st.columns(2)

            with col1:

                debit_choice = st.selectbox(
                    "Pilih Kolom Debit",
                    debit_options,
                    key="debit_choice"
                )

            with col2:

                credit_choice = st.selectbox(
                    "Pilih Kolom Kredit",
                    debit_options,
                    key="credit_choice"
                )

            if (
                debit_choice in numeric_columns
                and credit_choice in numeric_columns
            ):

                if debit_choice == credit_choice:

                    st.warning(
                        "Kolom debit dan kredit harus berbeda."
                    )

                else:

                    st.write(
                        "Hasil pemeriksaan akan tersimpan "
                        "untuk laporan audit."
                    )

                    st.dataframe(
                        debit_credit_report,
                        use_container_width=True
                    )

                    if abs(debit_total - credit_total) < 0.01:

                        st.success(
                            "Total debit dan kredit seimbang."
                        )

                    else:

                        st.warning(
                            "Total debit dan kredit tidak seimbang."
                        )

            else:

                st.info(
                    "Pilih kolom debit dan kredit terlebih dahulu."
                )

        else:

            st.info(
                "Data memerlukan minimal dua kolom numerik."
            )


# =========================================================
# 11. HALAMAN ANALISIS ANGGARAN
# =========================================================

elif menu == "Analisis Anggaran":

    st.markdown(
        '<div class="page-title">Analisis Anggaran dan Realisasi</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="page-description">'
        'Bandingkan nilai anggaran dengan realisasi transaksi.'
        '</div>',
        unsafe_allow_html=True
    )

    if df is None:

        st.warning("Silakan unggah data audit terlebih dahulu.")

    elif len(numeric_columns) < 2:

        st.warning(
            "Diperlukan minimal dua kolom numerik."
        )

    else:

        options = ["-- Pilih Kolom --"] + numeric_columns

        if st.session_state.budget_choice not in options:
            st.session_state.budget_choice = "-- Pilih Kolom --"

        if st.session_state.actual_choice not in options:
            st.session_state.actual_choice = "-- Pilih Kolom --"

        col1, col2 = st.columns(2)

        with col1:

            st.selectbox(
                "Pilih Kolom Anggaran",
                options,
                key="budget_choice"
            )

        with col2:

            st.selectbox(
                "Pilih Kolom Realisasi",
                options,
                key="actual_choice"
            )

        if (
            st.session_state.budget_choice in numeric_columns
            and st.session_state.actual_choice in numeric_columns
        ):

            if (
                st.session_state.budget_choice
                == st.session_state.actual_choice
            ):

                st.warning(
                    "Kolom anggaran dan realisasi harus berbeda."
                )

            else:

                st.subheader("Ringkasan Anggaran")

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Total Anggaran",
                    format_rupiah(budget_total)
                )

                c2.metric(
                    "Total Realisasi",
                    format_rupiah(actual_total)
                )

                c3.metric(
                    "Selisih",
                    format_rupiah(actual_total - budget_total)
                )

                st.subheader("Grafik Anggaran dan Realisasi")

                chart_data = pd.DataFrame({
                    "Jenis": ["Anggaran", "Realisasi"],
                    "Jumlah": [budget_total, actual_total]
                })

                fig = px.bar(
                    chart_data,
                    x="Jenis",
                    y="Jumlah",
                    text="Jumlah",
                    color="Jenis",
                    color_discrete_sequence=[
                        "#243B5A",
                        "#C5A45D"
                    ]
                )

                fig.update_layout(
                    showlegend=False,
                    plot_bgcolor="white",
                    paper_bgcolor="white"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

                st.subheader("Rincian Perbandingan")

                st.dataframe(
                    budget_df,
                    use_container_width=True
                )

                over_budget = budget_df[
                    budget_df["Keterangan"] == "Melebihi Anggaran"
                ]

                if not over_budget.empty:

                    st.warning(
                        f"Terdapat {len(over_budget)} baris "
                        "yang realisasinya melebihi anggaran."
                    )

                elif actual_total > budget_total:

                    st.warning(
                        "Total realisasi melebihi total anggaran."
                    )

                else:

                    st.success(
                        "Total realisasi tidak melebihi total anggaran."
                    )

        else:

            st.info(
                "Pilih kolom anggaran dan realisasi terlebih dahulu."
            )


# =========================================================
# 12. HALAMAN RINGKASAN TEMUAN
# =========================================================

elif menu == "Ringkasan Temuan Audit":

    st.markdown(
        '<div class="page-title">Ringkasan Temuan Audit</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="page-description">'
        'Gabungan seluruh hasil pemeriksaan data ADIWIA.'
        '</div>',
        unsafe_allow_html=True
    )

    if df is None:

        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        if not findings_df.empty:

            st.warning(
                f"Ditemukan {len(findings_df)} kategori temuan audit."
            )

            st.dataframe(
                findings_df,
                use_container_width=True
            )

            st.subheader("Grafik Jenis Temuan")

            fig = px.bar(
                findings_df,
                x="Jenis Temuan",
                y="Jumlah",
                color="Jenis Temuan",
                text="Jumlah",
                color_discrete_sequence=[
                    "#243B5A",
                    "#C5A45D",
                    "#7186A5",
                    "#8C9EB5",
                    "#B7A17A"
                ]
            )

            fig.update_layout(
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.success(
                "Belum ditemukan indikasi temuan berdasarkan "
                "pemeriksaan yang dilakukan."
            )


# =========================================================
# 13. HALAMAN AI AUDIT ANALYSIS
# =========================================================

elif menu == "AI Audit Analysis":

    st.markdown(
        '<div class="page-title">AI Audit Analysis</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="page-description">'
        'Analisis awal data transaksi menggunakan kecerdasan buatan.'
        '</div>',
        unsafe_allow_html=True
    )

    if df is None:

        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        st.info(
            "AI akan menganalisis ringkasan data dan hasil "
            "pemeriksaan yang telah dilakukan."
        )

        if st.button(
            "Mulai Analisis AI",
            use_container_width=True
        ):

            with st.spinner(
                "ADIWIA sedang menganalisis data..."
            ):

                prompt = f"""
                Anda adalah asisten digital audit yang membantu
                auditor melakukan pemeriksaan awal data keuangan.

                INFORMASI DATA:
                Jumlah transaksi: {len(df)}
                Jumlah kolom: {len(df.columns)}
                Data kosong: {total_missing}
                Data duplikat tambahan: {total_duplicate}
                Baris terindikasi outlier: {total_outlier}

                TEMUAN AUDIT:
                {findings_df.to_string(index=False)}

                PEMERIKSAAN DEBIT DAN KREDIT:
                {debit_credit_report.to_string(index=False)
                 if not debit_credit_report.empty else "Belum diperiksa."}

                ANALISIS ANGGARAN:
                {budget_df.head(100).to_string(index=False)
                 if not budget_df.empty else "Belum diperiksa."}

                CONTOH DATA TRANSAKSI:
                {df.head(100).to_string(index=False)}

                Berikan analisis dengan susunan:

                1. Gambaran umum data.
                2. Hasil pemeriksaan.
                3. Indikasi risiko atau ketidakwajaran.
                4. Rekomendasi tindak lanjut.
                5. Kesimpulan.

                Gunakan bahasa Indonesia formal dan mudah dipahami.
                Jangan menyatakan kecurangan tanpa bukti.
                Bedakan indikasi awal dan kesimpulan audit.
                """

                st.session_state.ai_result = ask_gemini(prompt)

        if st.session_state.ai_result:

            st.subheader("Hasil Analisis ADIWIA")

            st.markdown(
                st.session_state.ai_result
            )


# =========================================================
# 14. HALAMAN DOWNLOAD LAPORAN
# =========================================================

elif menu == "Download Laporan":

    st.markdown(
        '<div class="page-title">Download Laporan Audit</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="page-description">'
        'Unduh data transaksi dan seluruh hasil pemeriksaan '
        'dalam satu file Excel.'
        '</div>',
        unsafe_allow_html=True
    )

    if df is None:

        st.warning("Silakan unggah data audit terlebih dahulu.")

    else:

        st.subheader("Isi Laporan")

        st.write("""
        Laporan Excel terdiri dari:
        - Data Transaksi
        - Informasi Data
        - Data Kosong
        - Data Duplikat
        - Data Outlier
        - Pemeriksaan Debit Kredit
        - Anggaran Realisasi
        - Ringkasan Temuan
        - Analisis AI
        """)

        if st.button(
            "Buat Laporan Audit Excel",
            use_container_width=True
        ):

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

                    type_df.to_excel(
                        writer,
                        sheet_name="Informasi Data",
                        index=False
                    )

                    missing_df.to_excel(
                        writer,
                        sheet_name="Data Kosong",
                        index=False
                    )

                    duplicate_rows.to_excel(
                        writer,
                        sheet_name="Data Duplikat",
                        index=False
                    )

                    outlier_rows.to_excel(
                        writer,
                        sheet_name="Data Outlier",
                        index=False
                    )

                    debit_credit_report.to_excel(
                        writer,
                        sheet_name="Debit Kredit",
                        index=False
                    )

                    budget_df.to_excel(
                        writer,
                        sheet_name="Anggaran Realisasi",
                        index=False
                    )

                    findings_df.to_excel(
                        writer,
                        sheet_name="Ringkasan Temuan",
                        index=False
                    )

                    ai_text = st.session_state.ai_result

                    if not ai_text:
                        ai_text = "Analisis AI belum dilakukan."

                    pd.DataFrame({
                        "Hasil Analisis AI": [ai_text]
                    }).to_excel(
                        writer,
                        sheet_name="Analisis AI",
                        index=False
                    )

                output.seek(0)

                st.session_state.audit_report = output.getvalue()

                st.success("Laporan audit berhasil dibuat.")

            except Exception as e:

                st.error(
                    f"Gagal membuat laporan: {e}"
                )

        if st.session_state.get("audit_report"):

            st.download_button(
                label="Download Laporan Audit ADIWIA",
                data=st.session_state.audit_report,
                file_name="Laporan_Audit_ADIWIA.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True
            )


# =========================================================
# 15. FOOTER
# =========================================================

st.divider()

st.markdown("""
<div style="
    text-align:center;
    color:#718096;
    padding:15px;
    font-size:12px;
">
    <b>ADIWIA</b><br>
    Asisten Digital Audit Widianti & Adinda<br>
    Digital Audit Assistance | 2026
</div>
""", unsafe_allow_html=True)

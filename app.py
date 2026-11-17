
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

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

api_key = os.getenv("GEMINI_API_KEY")

try:
    if not api_key:
        api_key = st.secrets.get("GEMINI_API_KEY")

except Exception:
    pass

client = genai.Client(api_key=api_key) if api_key else None


# =====================================================
# 2. DESAIN DAN IDENTITAS ADIWIA
# =====================================================

st.markdown("""
<style>
.stApp {
    background-color: #F5F7FA;
}

.main-title {
    background: linear-gradient(120deg, #101D35, #294365);
    padding: 28px;
    border-radius: 16px;
    color: white;
    margin-bottom: 22px;
}

.logo-box {
    background: linear-gradient(135deg, #D6B66D, #F4DFA5);
    color: #14243D;
    width: 65px;
    height: 65px;
    border-radius: 15px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: Georgia, serif;
    font-size: 37px;
    font-weight: bold;
}

.brand-name {
    font-size: 30px;
    font-weight: 800;
    letter-spacing: 3px;
    margin: 0;
}

.brand-description {
    color: #D8DFE9;
    font-size: 13px;
    margin-top: 5px;
}

.section-heading {
    color: #172B49;
    font-size: 21px;
    font-weight: 750;
    margin-top: 15px;
    margin-bottom: 10px;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #E5E9F0;
    padding: 16px;
    border-radius: 12px;
}

.stDownloadButton button {
    background-color: #172B49;
    color: white;
    border-radius: 9px;
    border: none;
}

.stDownloadButton button:hover {
    background-color: #294365;
    color: white;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="main-title">
    <div style="display:flex; align-items:center; gap:18px;">
        <div class="logo-box">A</div>
        <div>
            <div class="brand-name">ADIWIA</div>
            <div class="brand-description">
                Asisten Digital Audit Widianti & Adinda
            </div>
            <div class="brand-description">
                Artificial Intelligence for Audit Assistance
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# =====================================================
# 3. FUNGSI PENDUKUNG
# =====================================================

def format_rupiah(value):
    return "Rp {:,.2f}".format(value)


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

            if any(code in error_message for code in [
                "503", "429", "500", "504", "UNAVAILABLE"
            ]):
                if attempt < retries - 1:
                    time.sleep(2 ** (attempt + 1))
                    continue

            return f"Analisis AI belum berhasil. Keterangan: {e}"

    return "Analisis AI gagal setelah beberapa percobaan."


def get_outlier_data(data):
    numeric_columns = data.select_dtypes(include="number").columns

    if len(numeric_columns) == 0:
        return pd.DataFrame(), 0

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

        lower_limit = q1 - (1.5 * iqr)
        upper_limit = q3 + (1.5 * iqr)

        detected = series[
            (series < lower_limit) |
            (series > upper_limit)
        ]

        outlier_indices.update(detected.index.tolist())

    result = data.loc[sorted(outlier_indices)].copy()

    return result, len(outlier_indices)


# =====================================================
# 4. UPLOAD DATA AUDIT
# =====================================================

st.markdown(
    '<div class="section-heading">📂 1. Upload Data Audit</div>',
    unsafe_allow_html=True
)

uploaded_file = st.file_uploader(
    "Unggah file transaksi keuangan dalam format Excel",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info(
        "Silakan unggah file Excel untuk mulai menggunakan "
        "fitur pemeriksaan ADIWIA."
    )

    st.markdown("""
    ### Fitur ADIWIA
    - Dashboard ringkasan audit
    - Informasi data transaksi
    - Pemeriksaan data kosong dan duplikat
    - Deteksi indikasi outlier
    - Pemeriksaan total debit dan kredit
    - Analisis anggaran dan realisasi
    - Ringkasan temuan audit
    - Analisis awal menggunakan AI
    - Download laporan audit Excel
    """)

    st.stop()


# =====================================================
# 5. MEMBACA DATA EXCEL
# =====================================================

try:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.astype(str).str.strip()

    if df.empty:
        st.error("File Excel tidak memiliki data transaksi.")
        st.stop()

    st.success("Data berhasil diunggah!")

except Exception as e:
    st.error(f"Gagal membaca file Excel: {e}")
    st.stop()


# =====================================================
# 6. PERSIAPAN DATA PEMERIKSAAN
# =====================================================

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

duplicate_rows = df[
    df.duplicated(keep=False)
].copy()

total_duplicate = int(df.duplicated().sum())

outlier_rows, total_outlier = get_outlier_data(df)

total_missing = int(df.isna().sum().sum())

numeric_columns = df.select_dtypes(
    include="number"
).columns.tolist()


# =====================================================
# 7. DASHBOARD ADIWIA
# =====================================================

st.markdown(
    '<div class="section-heading">📊 2. Dashboard ADIWIA</div>',
    unsafe_allow_html=True
)

st.write(
    "Dashboard menampilkan ringkasan data dan indikasi temuan "
    "berdasarkan pemeriksaan awal."
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Total Transaksi",
    f"{len(df):,}"
)

col2.metric(
    "Jumlah Kolom",
    f"{len(df.columns):,}"
)

col3.metric(
    "Total Data Kosong",
    f"{total_missing:,}"
)

col4, col5, col6 = st.columns(3)

col4.metric(
    "Data Duplikat",
    f"{total_duplicate:,}"
)

col5.metric(
    "Data Outlier",
    f"{total_outlier:,}"
)

col6.metric(
    "Jumlah Kolom Numerik",
    f"{len(numeric_columns):,}"
)

st.subheader("Grafik Ringkasan Pemeriksaan")

dashboard_data = pd.DataFrame({
    "Jenis Pemeriksaan": [
        "Data Kosong",
        "Data Duplikat",
        "Data Outlier"
    ],
    "Jumlah Temuan": [
        total_missing,
        total_duplicate,
        total_outlier
    ]
})

fig_dashboard = px.bar(
    dashboard_data,
    x="Jenis Pemeriksaan",
    y="Jumlah Temuan",
    text="Jumlah Temuan",
    color="Jenis Pemeriksaan",
    color_discrete_sequence=[
        "#243B5A",
        "#C5A45D",
        "#7186A5"
    ]
)

fig_dashboard.update_layout(
    showlegend=False,
    plot_bgcolor="white",
    paper_bgcolor="white",
    yaxis_title="Jumlah",
    xaxis_title="",
    margin=dict(t=25, b=20)
)

st.plotly_chart(
    fig_dashboard,
    use_container_width=True
)


# =====================================================
# 8. INFORMASI DATA
# =====================================================

st.markdown(
    '<div class="section-heading">📋 3. Informasi Data</div>',
    unsafe_allow_html=True
)

with st.expander("Lihat informasi data transaksi", expanded=True):

    st.write("**Jumlah Baris:**", len(df))
    st.write("**Jumlah Kolom:**", len(df.columns))
    st.write("**Nama Kolom:**", ", ".join(df.columns))

    st.write("**Pratinjau Data:**")
    st.dataframe(
        df.head(20),
        use_container_width=True
    )

    st.write("**Tipe Data:**")
    type_df = pd.DataFrame({
        "Nama Kolom": df.columns,
        "Tipe Data": df.dtypes.astype(str).values
    })

    st.dataframe(
        type_df,
        use_container_width=True
    )


# =====================================================
# 9. PEMERIKSAAN DATA AUDIT
# =====================================================

st.markdown(
    '<div class="section-heading">🔎 4. Pemeriksaan Data Audit</div>',
    unsafe_allow_html=True
)

st.subheader("A. Pemeriksaan Data Kosong")

if not missing_df.empty:
    st.warning("Ditemukan data kosong pada beberapa kolom.")

    st.dataframe(
        missing_df,
        use_container_width=True
    )
else:
    st.success("Tidak ditemukan data kosong.")

st.subheader("B. Pemeriksaan Data Duplikat")

if not duplicate_rows.empty:
    st.warning(
        f"Ditemukan {total_duplicate} baris duplikat "
        "berdasarkan pemeriksaan seluruh kolom."
    )

    st.dataframe(
        duplicate_rows,
        use_container_width=True
    )
else:
    st.success("Tidak ditemukan baris duplikat.")

st.subheader("C. Pemeriksaan Outlier")

if not outlier_rows.empty:
    st.warning(
        f"Ditemukan {total_outlier} baris yang terindikasi "
        "memiliki nilai outlier pada kolom numerik."
    )

    st.dataframe(
        outlier_rows,
        use_container_width=True
    )
else:
    st.success(
        "Tidak ditemukan indikasi outlier berdasarkan metode IQR."
    )

st.caption(
    "Catatan: Deteksi outlier menggunakan metode Interquartile Range "
    "(IQR) sebagai pemeriksaan awal."
)


# =====================================================
# 10. PEMERIKSAAN DEBIT DAN KREDIT
# =====================================================

st.subheader("D. Pemeriksaan Total Debit dan Kredit")

debit_total = None
credit_total = None
debit_credit_report = pd.DataFrame()

if numeric_columns:

    debit_options = ["-- Tidak dipilih --"] + numeric_columns

    debit_column = st.selectbox(
        "Pilih kolom Debit",
        debit_options,
        key="debit_column"
    )

    credit_column = st.selectbox(
        "Pilih kolom Kredit",
        debit_options,
        key="credit_column"
    )

    if (
        debit_column != "-- Tidak dipilih --"
        and credit_column != "-- Tidak dipilih --"
    ):

        if debit_column == credit_column:
            st.warning(
                "Kolom debit dan kredit tidak boleh menggunakan "
                "kolom yang sama."
            )

        else:
            debit_total = pd.to_numeric(
                df[debit_column],
                errors="coerce"
            ).sum()

            credit_total = pd.to_numeric(
                df[credit_column],
                errors="coerce"
            ).sum()

            difference = debit_total - credit_total

            debit_credit_report = pd.DataFrame({
                "Keterangan": [
                    "Total Debit",
                    "Total Kredit",
                    "Selisih"
                ],
                "Jumlah": [
                    debit_total,
                    credit_total,
                    difference
                ]
            })

            st.dataframe(
                debit_credit_report,
                use_container_width=True
            )

            if abs(difference) < 0.01:
                st.success(
                    "Total debit dan kredit seimbang."
                )
            else:
                st.warning(
                    "Total debit dan kredit tidak seimbang."
                )

    else:
        st.info(
            "Pilih kolom debit dan kredit untuk melakukan pemeriksaan."
        )

else:
    st.info(
        "Tidak terdapat kolom numerik untuk pemeriksaan debit dan kredit."
    )


# =====================================================
# 11. ANALISIS ANGGARAN DAN REALISASI
# =====================================================

st.markdown(
    '<div class="section-heading">💰 5. Analisis Anggaran dan Realisasi</div>',
    unsafe_allow_html=True
)

budget_df = pd.DataFrame()
budget_total = None
actual_total = None

if len(numeric_columns) >= 2:

    budget_column = st.selectbox(
        "Pilih kolom Anggaran",
        ["-- Tidak dipilih --"] + numeric_columns,
        key="budget_column"
    )

    actual_column = st.selectbox(
        "Pilih kolom Realisasi",
        ["-- Tidak dipilih --"] + numeric_columns,
        key="actual_column"
    )

    if (
        budget_column != "-- Tidak dipilih --"
        and actual_column != "-- Tidak dipilih --"
    ):

        if budget_column == actual_column:
            st.warning(
                "Kolom anggaran dan realisasi harus berbeda."
            )

        else:
            budget_values = pd.to_numeric(
                df[budget_column],
                errors="coerce"
            )

            actual_values = pd.to_numeric(
                df[actual_column],
                errors="coerce"
            )

            budget_df = pd.DataFrame({
                "Anggaran": budget_values,
                "Realisasi": actual_values
            })

            budget_df["Selisih"] = (
                budget_df["Realisasi"] -
                budget_df["Anggaran"]
            )

            budget_df["Persentase Realisasi"] = (
                budget_df["Realisasi"] /
                budget_df["Anggaran"].replace(0, pd.NA)
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

            st.subheader("Hasil Perbandingan")

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

            st.dataframe(
                budget_df,
                use_container_width=True
            )

            chart_budget = pd.DataFrame({
                "Jenis": ["Anggaran", "Realisasi"],
                "Jumlah": [budget_total, actual_total]
            })

            fig_budget = px.bar(
                chart_budget,
                x="Jenis",
                y="Jumlah",
                text="Jumlah",
                color="Jenis",
                color_discrete_sequence=[
                    "#243B5A",
                    "#C5A45D"
                ],
                title="Perbandingan Total Anggaran dan Realisasi"
            )

            fig_budget.update_layout(
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white"
            )

            st.plotly_chart(
                fig_budget,
                use_container_width=True
            )

            if actual_total > budget_total:
                st.warning(
                    "Total realisasi lebih besar daripada total anggaran."
                )
            else:
                st.success(
                    "Total realisasi tidak melebihi total anggaran."
                )

    else:
        st.info(
            "Pilih kolom anggaran dan realisasi untuk memulai analisis."
        )

else:
    st.info(
        "Diperlukan minimal dua kolom numerik untuk analisis anggaran."
    )


# =====================================================
# 12. RINGKASAN TEMUAN AUDIT
# =====================================================

st.markdown(
    '<div class="section-heading">📝 6. Ringkasan Temuan Audit</div>',
    unsafe_allow_html=True
)

findings = []

# Temuan data kosong
for item in missing_data:
    findings.append({
        "Jenis Temuan": "Data Kosong",
        "Keterangan": (
            f"Kolom {item['Kolom']} memiliki "
            f"{item['Jumlah Data Kosong']} data kosong."
        ),
        "Jumlah": item["Jumlah Data Kosong"]
    })

# Temuan duplikat
if total_duplicate > 0:
    findings.append({
        "Jenis Temuan": "Data Duplikat",
        "Keterangan": (
            f"Ditemukan {total_duplicate} baris duplikat "
            "berdasarkan seluruh kolom."
        ),
        "Jumlah": total_duplicate
    })

# Temuan outlier
if total_outlier > 0:
    findings.append({
        "Jenis Temuan": "Outlier",
        "Keterangan": (
            f"Ditemukan {total_outlier} baris yang terindikasi "
            "memiliki nilai outlier pada kolom numerik."
        ),
        "Jumlah": total_outlier
    })

# Temuan debit dan kredit
if debit_total is not None and credit_total is not None:
    difference = debit_total - credit_total

    if abs(difference) >= 0.01:
        findings.append({
            "Jenis Temuan": "Debit dan Kredit",
            "Keterangan": (
                f"Total debit dan kredit tidak seimbang. "
                f"Selisih sebesar {format_rupiah(abs(difference))}."
            ),
            "Jumlah": 1
        })

# Temuan anggaran dan realisasi
if budget_total is not None and actual_total is not None:
    if actual_total > budget_total:
        findings.append({
            "Jenis Temuan": "Anggaran dan Realisasi",
            "Keterangan": (
                "Total realisasi melebihi total anggaran sebesar "
                f"{format_rupiah(actual_total - budget_total)}."
            ),
            "Jumlah": 1
        })

    if budget_df["Keterangan"].eq("Melebihi Anggaran").any():
        findings.append({
            "Jenis Temuan": "Realisasi per Baris",
            "Keterangan": (
                "Terdapat transaksi yang realisasinya melebihi "
                "anggaran pada baris terkait."
            ),
            "Jumlah": int(
                budget_df["Keterangan"].eq("Melebihi Anggaran").sum()
            )
        })


findings_df = pd.DataFrame(
    findings,
    columns=["Jenis Temuan", "Keterangan", "Jumlah"]
)

if not findings_df.empty:
    st.warning(
        f"ADIWIA menemukan {len(findings_df)} kategori temuan audit "
        "yang perlu diperiksa lebih lanjut."
    )

    st.dataframe(
        findings_df,
        use_container_width=True
    )

else:
    st.success(
        "Belum ditemukan indikasi temuan berdasarkan pemeriksaan yang dilakukan."
    )


# =====================================================
# 13. AI AUDIT ANALYSIS
# =====================================================

st.markdown(
    '<div class="section-heading">🤖 7. AI Audit Analysis</div>',
    unsafe_allow_html=True
)

st.write(
    "Gunakan AI untuk memperoleh analisis awal berdasarkan "
    "data transaksi dan hasil pemeriksaan ADIWIA."
)

if st.button(
    "✨ Mulai Analisis AI",
    use_container_width=True
):

    with st.spinner("ADIWIA sedang menganalisis data..."):

        prompt = f"""
        Anda adalah asisten digital audit yang membantu auditor
        melakukan pemeriksaan awal data keuangan.

        Analisis data berikut secara objektif dan hati-hati.

        INFORMASI DATA:
        Jumlah transaksi: {len(df)}
        Jumlah kolom: {len(df.columns)}
        Data kosong: {total_missing}
        Data duplikat: {total_duplicate}
        Data outlier: {total_outlier}

        TEMUAN AUDIT:
        {findings_df.to_string(index=False)}

        HASIL DEBIT DAN KREDIT:
        {debit_credit_report.to_string(index=False)
         if not debit_credit_report.empty else "Belum diperiksa."}

        HASIL ANGGARAN DAN REALISASI:
        {budget_df.head(100).to_string(index=False)
         if not budget_df.empty else "Belum diperiksa."}

        CONTOH DATA TRANSAKSI:
        {df.head(100).to_string(index=False)}

        Berikan hasil dengan susunan:
        1. Gambaran umum data.
        2. Hasil pemeriksaan.
        3. Indikasi risiko atau ketidakwajaran.
        4. Rekomendasi tindak lanjut.
        5. Kesimpulan.

        Jangan menyatakan adanya kecurangan tanpa bukti.
        Bedakan indikasi awal dengan kesimpulan audit.
        Gunakan bahasa Indonesia yang formal dan mudah dipahami.
        """

        ai_result = ask_gemini(prompt)

        st.session_state["ai_result"] = ai_result


if "ai_result" in st.session_state:

    st.subheader("Hasil Analisis ADIWIA")

    st.markdown(st.session_state["ai_result"])


# =====================================================
# 14. DOWNLOAD LAPORAN AUDIT
# =====================================================

st.markdown(
    '<div class="section-heading">📥 8. Download Laporan Audit</div>',
    unsafe_allow_html=True
)

try:
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
        type_df.to_excel(
            writer,
            sheet_name="Informasi Data",
            index=False
        )

        # Data kosong
        missing_df.to_excel(
            writer,
            sheet_name="Data Kosong",
            index=False
        )

        # Data duplikat
        duplicate_rows.to_excel(
            writer,
            sheet_name="Data Duplikat",
            index=False
        )

        # Data outlier
        outlier_rows.to_excel(
            writer,
            sheet_name="Data Outlier",
            index=False
        )

        # Pemeriksaan debit dan kredit
        debit_credit_report.to_excel(
            writer,
            sheet_name="Pemeriksaan Debit Kredit",
            index=False
        )

        # Anggaran dan realisasi
        budget_df.to_excel(
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

        # Hasil analisis AI
        ai_text = st.session_state.get(
            "ai_result",
            "Analisis AI belum dilakukan."
        )

        pd.DataFrame({
            "Hasil Analisis AI": [ai_text]
        }).to_excel(
            writer,
            sheet_name="Analisis AI",
            index=False
        )

    output.seek(0)

    st.download_button(
        label="📥 Download Laporan Audit Excel",
        data=output.getvalue(),
        file_name="Laporan_Audit_ADIWIA.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True
    )

except Exception as e:
    st.error(f"Gagal membuat laporan audit: {e}")


# =====================================================
# 15. FOOTER
# =====================================================

st.divider()

st.markdown("""
<div style="text-align:center; color:#718096; padding:15px;">
    <b>ADIWIA</b><br>
    Asisten Digital Audit Widianti & Adinda<br>
    <small>Digital Audit Assistance | 2026</small>
</div>
""", unsafe_allow_html=True)

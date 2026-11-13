
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# =====================================
# KONFIGURASI ADIWIA
# =====================================

st.set_page_config(
    page_title="ADIWIA",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 ADIWIA")
st.subheader("Asisten Digital Audit Widianti & Adinda")
st.write(
    "Sistem Digital untuk Membantu Pemeriksaan, "
    "Analisis, dan Evaluasi Data Keuangan."
)

st.divider()

# =====================================
# UPLOAD DATA
# =====================================

st.header("1. Upload Data Keuangan")

uploaded_file = st.file_uploader(
    "Upload file transaksi keuangan",
    type=["xlsx", "xls", "csv"]
)

if uploaded_file is not None:

    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if df.empty:
            st.warning("File tidak memiliki data.")
            st.stop()

        st.success("Data berhasil diunggah!")

        # =====================================
        # INFORMASI DATA
        # =====================================

        st.header("2. Informasi Data")

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Transaksi", len(df))
        col2.metric("Jumlah Kolom", len(df.columns))
        col3.metric(
            "Data Kosong",
            int(df.isnull().sum().sum())
        )

        st.dataframe(df, use_container_width=True)

        # =====================================
        # PEMERIKSAAN AUDIT
        # =====================================

        st.divider()
        st.header("3. Analisis dan Pemeriksaan Audit")

        findings = []
        detail_results = {}

        # A. Pemeriksaan data kosong

        missing = df.isnull().sum()

        for column, count in missing.items():
            if count > 0:
                findings.append({
                    "Jenis Temuan": "Data Tidak Lengkap",
                    "Kolom": str(column),
                    "Jumlah": int(count),
                    "Keterangan": (
                        f"Terdapat {count} data kosong "
                        f"pada kolom {column}."
                    )
                })

        detail_results["Data Kosong"] = df[
            df.isnull().any(axis=1)
        ]

        # B. Pemeriksaan duplikasi

        duplicate_mask = df.duplicated(keep=False)

        duplicate_count = int(duplicate_mask.sum())

        if duplicate_count > 0:
            findings.append({
                "Jenis Temuan": "Transaksi Duplikat",
                "Kolom": "Seluruh kolom",
                "Jumlah": duplicate_count,
                "Keterangan": (
                    "Ditemukan baris dengan data identik "
                    "yang perlu diperiksa."
                )
            })

        detail_results["Duplikat"] = df[duplicate_mask]

        # C. Pemeriksaan nominal tidak wajar

        numeric_columns = df.select_dtypes(
            include=np.number
        ).columns.tolist()

        amount_candidates = [
            col for col in numeric_columns
            if any(word in str(col).lower()
                   for word in [
                       "nominal", "jumlah", "amount",
                       "nilai", "transaksi"
                   ])
        ]

        amount_col = None
        unusual_mask = pd.Series(False, index=df.index)

        if amount_candidates:

            amount_col = st.selectbox(
                "Pilih kolom nominal transaksi",
                amount_candidates
            )

            values = pd.to_numeric(
                df[amount_col], errors="coerce"
            ).dropna()

            if len(values) >= 4:

                q1 = values.quantile(0.25)
                q3 = values.quantile(0.75)
                iqr = q3 - q1

                lower = q1 - (1.5 * iqr)
                upper = q3 + (1.5 * iqr)

                numeric_amount = pd.to_numeric(
                    df[amount_col], errors="coerce"
                )

                unusual_mask = (
                    (numeric_amount < lower) |
                    (numeric_amount > upper)
                ).fillna(False)

                unusual_count = int(unusual_mask.sum())

                if unusual_count > 0:
                    findings.append({
                        "Jenis Temuan": "Nominal Tidak Wajar",
                        "Kolom": str(amount_col),
                        "Jumlah": unusual_count,
                        "Keterangan": (
                            "Terdapat nominal di luar batas "
                            "statistik metode IQR."
                        )
                    })

        detail_results["Nominal Tidak Wajar"] = df[
            unusual_mask
        ]

        # D. Pemeriksaan debit dan kredit

        debit_cols = [
            col for col in numeric_columns
            if "debit" in str(col).lower()
        ]

        credit_cols = [
            col for col in numeric_columns
            if "kredit" in str(col).lower()
            or "credit" in str(col).lower()
        ]

        imbalance_mask = pd.Series(False, index=df.index)

        if debit_cols and credit_cols:

            debit = pd.to_numeric(
                df[debit_cols[0]], errors="coerce"
            )

            credit = pd.to_numeric(
                df[credit_cols[0]], errors="coerce"
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
                    "Kolom": (
                        f"{debit_cols[0]} dan {credit_cols[0]}"
                    ),
                    "Jumlah": imbalance_count,
                    "Keterangan": (
                        "Terdapat perbedaan nilai debit "
                        "dan kredit pada baris transaksi."
                    )
                })

        detail_results["Debit Kredit"] = df[
            imbalance_mask
        ]

        # =====================================
        # HASIL AUDIT
        # =====================================

        st.divider()
        st.header("4. Hasil Temuan Audit")

        result = pd.DataFrame(findings)

        if not result.empty:

            st.warning(
                f"Ditemukan {len(result)} jenis indikasi "
                "yang memerlukan pemeriksaan lanjutan."
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

        # =====================================
        # DETAIL TEMUAN
        # =====================================

        st.divider()
        st.header("5. Detail Pemeriksaan")

        for title, detail in detail_results.items():

            if not detail.empty:

                with st.expander(f"Lihat {title}"):

                    st.dataframe(
                        detail,
                        use_container_width=True
                    )

        # =====================================
        # DOWNLOAD LAPORAN
        # =====================================

        st.divider()
        st.header("6. Unduh Laporan Audit")

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

            result.to_excel(
                writer,
                sheet_name="Temuan Audit",
                index=False
            )

        st.download_button(
            label="📥 Download Laporan Audit",
            data=output.getvalue(),
            file_name="Laporan_Audit_ADIWIA.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")

else:
    st.info(
        "Silakan upload data keuangan untuk memulai "
        "pemeriksaan menggunakan ADIWIA."
    )

# =====================================
# FOOTER
# =====================================

st.divider()

st.caption(
    "ADIWIA | Asisten Digital Audit Widianti & Adinda"
)

st.caption(
    "Hasil pemeriksaan merupakan indikasi awal "
    "dan tetap memerlukan verifikasi auditor."
)

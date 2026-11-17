import os
import time
from io import BytesIO
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

try:
    from google import genai
except ImportError:
    genai = None


# =========================================================
# 1. KONFIGURASI APLIKASI
# =========================================================
load_dotenv()

st.set_page_config(
    page_title="ADIWIA",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#0B1B36"          # warna sidebar (lebih gelap, sesuai desain baru)
NAVY_DARK = "#08142B"
NAVY_LIGHT = "#243F60"
GOLD = "#F1C453"          # emas utama (judul menu & menu aktif)
GOLD_DARK = "#D6A23A"
LIGHT_BG = "#F4F6F9"


# ---------------------------------------------------------
# Ikon menu (SVG garis) -> dipakai lewat CSS
# ---------------------------------------------------------
def _stroke(inner):
    return ('<g fill="none" stroke="__C__" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round">' + inner + '</g>')


SVG_ICONS = {
    "Dashboard": '<path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>',
    "Upload Data Audit": '<path d="M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>',
    "Informasi Data": '<ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 8.5v3c0 1.66 3.58 3 8 3s8-1.34 8-3v-3c0 1.66-3.58 3-8 3s-8-1.34-8-3z"/><path d="M4 13.5v3c0 1.66 3.58 3 8 3s8-1.34 8-3v-3c0 1.66-3.58 3-8 3s-8-1.34-8-3z"/>',
    "Pemeriksaan Data Audit": '<path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>',
    "Analisis Anggaran dan Realisasi": '<rect x="3" y="14" width="5" height="7" rx="1"/><rect x="10" y="9" width="5" height="12" rx="1"/><rect x="17" y="3" width="5" height="18" rx="1"/>',
    "Fraud Detection": '<path fill-rule="evenodd" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zM11 7h2v6h-2zM11 15h2v2h-2z"/>',
    "Risk Assessment": '<path fill-rule="evenodd" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/>',
    "Ringkasan Temuan Audit": '<path fill-rule="evenodd" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM8 8h4v1.8H8zM8 12h8v1.8H8zM8 16h8v1.8H8z"/>',
    "AI Audit Analysis": _stroke('<rect x="5" y="5" width="14" height="14" rx="3"/><circle cx="9.5" cy="10" r="1.2"/><circle cx="14.5" cy="14" r="1.2"/><path d="M9.5 11.2v2.3h2.8M14.5 12.8v-2.3h-2.8"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>'),
    "Download Laporan Audit": _stroke('<path d="M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/><path d="M12 3v12M7 10l5 5 5-5"/>'),
}

MENU_ITEMS = (SVG_ICONS.keys())


def svg_data_uri(inner, color):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="{color}">' + inner.replace("__C__", color) + "</svg>"
    )
    return "url(\"data:image/svg+xml;utf8," + quote(svg) + "\")"


def build_menu_icon_css():
    css = []
    sel = '[data-testid="stSidebar"] div[role="radiogroup"] > label'
    for i, name in enumerate(MENU_ITEMS, start=1):
        normal = svg_data_uri(SVG_ICONS[name], "#FFFFFF")
        active = svg_data_uri(SVG_ICONS[name], GOLD)
        css.append(f"{sel}:nth-child({i})::before {{ background-image: {normal}; }}")
        css.append(f"{sel}:nth-child({i}):has(input:checked)::before {{ background-image: {active}; }}")
    return "\n".join(css)


st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {LIGHT_BG}; }}

    /* ---------- SIDEBAR ---------- */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {NAVY_DARK}, {NAVY});
    }}
    [data-testid="stSidebar"] * {{ color: white !important; }}

    /* ---------- LOGO ---------- */
    .aw-logo {{
        width: 104px; height: 104px; margin: 10px auto 16px auto;
        display: flex; justify-content: center; align-items: center;
        background: linear-gradient(135deg, #F7D774 0%, {GOLD} 45%, {GOLD_DARK} 100%);
        border-radius: 28px;
        box-shadow: 0 8px 20px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.35);
    }}
    .aw-logo span {{
        color: {NAVY} !important;
        font-family: 'Times New Roman', Georgia, serif;
        font-size: 56px; font-weight: 700; letter-spacing: -4px;
        line-height: 1; margin-left: -4px;
    }}
    .aw-title {{
        text-align: center; font-size: 28px; font-weight: 800;
        letter-spacing: 1px; margin: 4px 0 2px 0; color: white !important;
    }}
    .aw-sub {{
        text-align: center; font-size: 14px; line-height: 1.6;
        margin: 0; color: #E8EDF4 !important;
    }}
    .aw-divider {{
        height: 1px; background: rgba(255,255,255,.28); margin: 18px 4px 20px 4px;
    }}
    .aw-menu-title {{
        color: {GOLD} !important; font-weight: 700; font-size: 15px;
        letter-spacing: .3px; margin: 0 0 8px 6px;
    }}
    .aw-menu-title * {{ color: {GOLD} !important; }}

    /* ---------- MENU UTAMA (radio -> menu berikon) ---------- */
    [data-testid="stSidebar"] div[role="radiogroup"] {{ gap: 2px; }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label {{
        display: flex; align-items: center; gap: 14px;
        padding: 8px 6px; border-radius: 8px; cursor: pointer;
        width: 100%; transition: background .15s ease;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{
        background: rgba(255,255,255,.07);
    }}
    /* sembunyikan bulatan radio */
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{
        display: none !important;
    }}
    /* kotak ikon */
    [data-testid="stSidebar"] div[role="radiogroup"] > label::before {{
        content: ""; flex: 0 0 24px; width: 24px; height: 24px;
        background-repeat: no-repeat; background-position: center;
        background-size: 21px 21px;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label p {{
        font-size: 15px; font-weight: 500; margin: 0;
    }}
    /* menu aktif -> emas */
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{
        background: transparent;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {{
        color: {GOLD} !important; font-weight: 700;
    }}
    {build_menu_icon_css()}

    /* ---------- KONTEN UTAMA ---------- */
    .hero {{
        background: linear-gradient(115deg, #08142B 0%, {NAVY} 58%, #34516F 100%);
        color: white; padding: 30px 32px; border-radius: 18px; margin-bottom: 22px;
        box-shadow: 0 8px 22px rgba(20,36,58,.12);
    }}
    .hero h1 {{ color: #F1D18A; margin-bottom: 4px; letter-spacing: 2px; }}
    .hero h3 {{ color: white; margin-top: 0; }}
    .hero p {{ color: #E8EDF4; max-width: 850px; line-height: 1.65; }}
    .feature-grid {{
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
        column-gap: 34px; row-gap: 18px; margin: 12px 0 22px 0;
    }}
    .feature-item {{
        display: flex; gap: 13px; align-items: flex-start;
        padding: 7px 0; border: none; outline: none; background: transparent;
    }}
    .feature-icon {{
        min-width: 38px; height: 38px; display: flex; align-items: center;
        justify-content: center; border-radius: 11px; background: #E9EEF4;
        font-size: 19px;
    }}
    .feature-title {{ color: #172A42; font-weight: 700; margin: 0 0 3px 0; }}
    .feature-desc {{ color: #64748B; font-size: 13px; line-height: 1.5; margin: 0; }}
    @media (max-width: 700px) {{
        .feature-grid {{ grid-template-columns: 1fr; }}
    }}
    .small-note {{ color: #657286; font-size:  .88rem; }}
    div[data-testid="stMetric"] {{
        background: white; padding: 14px; border-radius: 12px;
        border: 1px solid #E5E9EF;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 2. SESSION STATE
# =========================================================
defaults = {
    "data": None,
    "file_name": None,
    "fraud_data": None,
    "ai_result": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# 3. FUNGSI UMUM
# =========================================================
def format_number(value):
    try:
        return f"{float(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except (ValueError, TypeError):
        return str(value)


def get_numeric_columns(data):
    return data.select_dtypes(include="number").columns.tolist()


def get_missing_data(data):
    result = data.isna().sum().reset_index()
    result.columns = ["Nama Kolom", "Jumlah Data Kosong"]
    return result[result["Jumlah Data Kosong"] > 0].sort_values(
        "Jumlah Data Kosong", ascending=False
    )


def get_duplicate_data(data):
    return data[data.duplicated(keep=False)].copy()


def get_outlier_data(data):
    numeric_cols = get_numeric_columns(data)
    records = []
    for col in numeric_cols:
        series = pd.to_numeric(data[col], errors="coerce").dropna()
        if len(series) < 4:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = pd.to_numeric(data[col], errors="coerce").lt(lower) | pd.to_numeric(
            data[col], errors="coerce"
        ).gt(upper)
        for idx in data.index[mask.fillna(False)]:
            records.append(
                {
                    "Nomor Baris": int(data.index.get_loc(idx)) + 1,
                    "Kolom Pemeriksaan": col,
                    "Nilai": data.loc[idx, col],
                    "Batas Bawah": lower,
                    "Batas Atas": upper,
                }
            )
    return pd.DataFrame(records)


def get_fraud_detection(data):
    """Menyaring indikasi awal, bukan menetapkan bahwa kecurangan benar terjadi."""
    result = data.copy().reset_index(drop=True)
    result.insert(0, "Nomor Baris", range(1, len(result) + 1))
    reasons = [[] for _ in range(len(result))]

    duplicate_mask = data.reset_index(drop=True).duplicated(keep=False)
    for i in range(len(result)):
        if duplicate_mask.iloc[i]:
            reasons[i].append("Baris duplikat")

    for col in get_numeric_columns(data):
        series = pd.to_numeric(data[col], errors="coerce")
        valid = series.dropna()
        if len(valid) >= 4:
            q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                mask = series.lt(lower) | series.gt(upper)
                for i in range(len(result)):
                    if bool(mask.iloc[i]):
                        reasons[i].append(f"Nilai tidak biasa pada {col}")
        negative_mask = series.lt(0)
        for i in range(len(result)):
            if bool(negative_mask.iloc[i]):
                reasons[i].append(f"Nilai negatif pada {col}")

    result["Indikasi Pemeriksaan"] = ["; ".join(dict.fromkeys(x)) for x in reasons]
    result["Status"] = result["Indikasi Pemeriksaan"].apply(
        lambda x: "Perlu Ditinjau" if x else "Tidak Ditandai"
    )
    return result[result["Indikasi Pemeriksaan"] != ""].copy()


def get_debit_credit_check(data, debit_col, credit_col):
    debit_total = pd.to_numeric(data[debit_col], errors="coerce").fillna(0).sum()
    credit_total = pd.to_numeric(data[credit_col], errors="coerce").fillna(0).sum()
    difference = debit_total - credit_total
    return debit_total, credit_total, difference


def calculate_risk_assessment(data, fraud_data, missing_data, duplicate_data, outlier_data,
                              debit_col=None, credit_col=None):
    """Skor heuristik awal 0-100, bukan model risiko yang tervalidasi."""
    score = 0
    details = []

    total_cells = max(data.shape[0] * data.shape[1], 1)
    missing_count = int(data.isna().sum().sum())
    missing_rate = missing_count / total_cells
    if missing_count:
        points = 5 if missing_rate < 0.10 else 10
        score += points
        details.append(f"Data kosong: {missing_count} sel ({points} poin)")

    duplicate_rows = len(data[data.duplicated(keep=False)])
    if duplicate_rows:
        points = 15 if duplicate_rows >= 5 else 8
        score += points
        details.append(f"Baris duplikat: {duplicate_rows} baris ({points} poin)")

    outlier_rows = (
        outlier_data["Nomor Baris"].nunique()
        if not outlier_data.empty and "Nomor Baris" in outlier_data.columns
        else 0
    )
    if outlier_rows:
        points = 20 if outlier_rows >= 5 else 10
        score += points
        details.append(f"Nilai tidak biasa: {outlier_rows} baris ({points} poin)")

    fraud_rows = len(fraud_data)
    if fraud_rows:
        points = 30 if fraud_rows >= 5 else 20
        score += points
        details.append(f"Indikasi transaksi perlu ditinjau: {fraud_rows} baris ({points} poin)")

    if debit_col and credit_col:
        debit_total, credit_total, difference = get_debit_credit_check(
            data, debit_col, credit_col
        )
        if abs(difference) > 0.01:
            score += 25
            details.append("Total debit dan kredit tidak seimbang (25 poin)")

    score = min(score, 100)
    category = "Tinggi" if score >= 50 else "Sedang" if score >= 25 else "Rendah"
    return score, category, details


def build_findings(data, missing_data, duplicate_data, outlier_data, fraud_data,
                   risk_score, risk_category):
    findings = []
    if missing_data.empty:
        findings.append("Tidak ditemukan data kosong.")
    else:
        findings.append(
            f"Ditemukan {int(data.isna().sum().sum())} sel kosong pada "
            f"{len(missing_data)} kolom."
        )
    if duplicate_data.empty:
        findings.append("Tidak ditemukan baris duplikat.")
    else:
        findings.append(f"Ditemukan {len(duplicate_data)} baris yang terindikasi duplikat.")
    if outlier_data.empty:
        findings.append("Tidak ditemukan nilai di luar batas IQR pada kolom numerik yang diperiksa.")
    else:
        findings.append(
            f"Ditemukan {outlier_data['Nomor Baris'].nunique()} baris dengan nilai tidak biasa."
        )
    if fraud_data.empty:
        findings.append("Tidak ada baris yang ditandai oleh aturan penyaringan indikasi awal.")
    else:
        findings.append(
            f"{len(fraud_data)} baris memiliki indikasi yang perlu ditinjau lebih lanjut."
        )
    findings.append(f"Skor risiko awal {risk_score}/100 dengan kategori {risk_category}.")
    return findings


def generate_ai_analysis(data, findings):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "API key Gemini belum diatur. Tambahkan GEMINI_API_KEY pada Streamlit Secrets."
    if genai is None:
        return "Library google-genai belum terpasang. Periksa requirements.txt."
    try:
        client = genai.Client(api_key=api_key)
        numeric_summary = data.describe(include="all").fillna("").to_string()
        sample = data.head(30).fillna("").to_string(index=False)
        prompt = f"""
Anda adalah asisten pendukung pemeriksaan audit data keuangan.
Analisis data berikut secara hati-hati dan gunakan bahasa Indonesia yang mudah dipahami.
Jangan menyatakan bahwa fraud terbukti. Bedakan indikasi, risiko, dan fakta.
Jangan mengarang informasi yang tidak tersedia. Berikan:
1. Gambaran umum data.
2. Hal-hal yang perlu diperiksa auditor.
3. Kemungkinan penyebab anomali.
4. Rekomendasi tindak lanjut.
5. Keterbatasan analisis.

Ringkasan temuan otomatis:
{chr(10).join("- " + x for x in findings)}

Statistik data:
{numeric_summary}

Contoh maksimal 30 baris:
{sample}
"""
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        last_error = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response.text or "AI tidak menghasilkan jawaban."
            except Exception as exc:
                last_error = exc
                message = str(exc)
                if any(code in message for code in ["503", "429", "500", "504"]) and attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                break
        return (
            "Analisis AI belum berhasil dijalankan.\n\n"
            f"Pesan sistem: {last_error}\n\n"
            "Jika muncul 503 atau 429, layanan model mungkin sedang sibuk. "
            "Coba kembali beberapa saat lagi."
        )
    except Exception as exc:
        return f"Terjadi kendala saat menyiapkan analisis AI: {exc}"


def create_excel_report(data, missing_data, duplicate_data, outlier_data, fraud_data,
                        risk_score, risk_category, risk_details, findings, ai_result,
                        budget_result=None):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        data.to_excel(writer, sheet_name="Data Transaksi", index=False)
        missing_data.to_excel(writer, sheet_name="Data Kosong", index=False)
        duplicate_data.to_excel(writer, sheet_name="Data Duplikat", index=False)
        outlier_data.to_excel(writer, sheet_name="Data Outlier", index=False)
        fraud_data.to_excel(writer, sheet_name="Fraud Detection", index=False)

        pd.DataFrame(
            {"Keterangan": ["Skor Risiko", "Kategori"], "Hasil": [risk_score, risk_category]}
        ).to_excel(writer, sheet_name="Risk Assessment", index=False)
        pd.DataFrame({"Faktor Risiko": risk_details or ["Tidak ada faktor risiko yang ditandai."]}).to_excel(
            writer, sheet_name="Detail Risiko", index=False
        )
        pd.DataFrame({"Ringkasan Temuan": findings}).to_excel(
            writer, sheet_name="Ringkasan Temuan", index=False
        )
        pd.DataFrame({"Analisis AI": [ai_result or "Belum dilakukan"]}).to_excel(
            writer, sheet_name="Analisis AI", index=False
        )
        if budget_result is not None:
            budget_result.to_excel(writer, sheet_name="Anggaran Realisasi", index=False)

    output.seek(0)
    return output


# =========================================================
# 4. SIDEBAR / NAVIGASI
# =========================================================
with st.sidebar:
    st.markdown(
        """
        <div class="aw-logo"><span>AW</span></div>
        <div class="aw-title">ADIWIA</div>
        <p class="aw-sub">Asisten Digital Audit<br>Widianti &amp; Adinda</p>
        <div class="aw-divider"></div>
        <div class="aw-menu-title">MENU UTAMA</div>
        """,
        unsafe_allow_html=True,
    )

    menu = st.radio(
        "MENU UTAMA",
        MENU_ITEMS,
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("ADIWIA • Asisten Pendukung Audit")


# =========================================================
# 5. DATA YANG SUDAH DIUNGGAH
# =========================================================
data = st.session_state.data

if menu == "Dashboard":
    st.markdown(
        """
        <div class="hero">
            <h1>ADIWIA</h1>
            <h3>Asisten Digital Audit Widianti & Adinda</h3>
            <p>Asisten digital berbasis Artificial Intelligence untuk membantu pemeriksaan,
            analisis, dan evaluasi data keuangan secara lebih terstruktur.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("Tentang ADIWIA")
    st.write(
        "ADIWIA dirancang sebagai alat bantu pemeriksaan data audit. Aplikasi ini membantu "
        "pengguna mengidentifikasi masalah kualitas data, melihat indikasi transaksi yang "
        "perlu ditinjau, menilai risiko awal, serta menyusun ringkasan hasil pemeriksaan."
    )

    st.subheader("Fitur Utama")
    st.markdown(
        """
        <div class="feature-grid">
          <div class="feature-item"><div class="feature-icon">📂</div><div><p class="feature-title">Upload Data Audit</p><p class="feature-desc">Mengimpor data transaksi dari Excel atau CSV.</p></div></div>
          <div class="feature-item"><div class="feature-icon">📋</div><div><p class="feature-title">Informasi Data</p><p class="feature-desc">Melihat struktur, tipe, dan statistik data.</p></div></div>
          <div class="feature-item"><div class="feature-icon">🔎</div><div><p class="feature-title">Pemeriksaan Data Audit</p><p class="feature-desc">Memeriksa data kosong, duplikat, outlier, serta debit dan kredit.</p></div></div>
          <div class="feature-item"><div class="feature-icon">📊</div><div><p class="feature-title">Analisis Anggaran dan Realisasi</p><p class="feature-desc">Membandingkan nilai anggaran dengan realisasi.</p></div></div>
          <div class="feature-item"><div class="feature-icon">🕵️</div><div><p class="feature-title">Fraud Detection</p><p class="feature-desc">Menandai pola transaksi yang perlu ditinjau lebih lanjut.</p></div></div>
          <div class="feature-item"><div class="feature-icon">⚠️</div><div><p class="feature-title">Risk Assessment</p><p class="feature-desc">Memberikan penilaian tingkat risiko awal.</p></div></div>
          <div class="feature-item"><div class="feature-icon">📝</div><div><p class="feature-title">Ringkasan Temuan Audit</p><p class="feature-desc">Merangkum hasil pemeriksaan data.</p></div></div>
          <div class="feature-item"><div class="feature-icon">🤖</div><div><p class="feature-title">AI Audit Analysis</p><p class="feature-desc">Menyusun analisis dan rekomendasi berbantuan AI.</p></div></div>
          <div class="feature-item"><div class="feature-icon">📥</div><div><p class="feature-title">Download Laporan Audit</p><p class="feature-desc">Mengunduh hasil pemeriksaan dalam format Excel.</p></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Alur Penggunaan")
    st.info(
        "Upload Data → Informasi Data → Pemeriksaan Data → Fraud Detection dan Analisis "
        "Anggaran → Risk Assessment → AI Audit Analysis → Ringkasan Temuan → Download Laporan"
    )
    if data is not None:
        st.success(f"Data aktif: {st.session_state.file_name} • {len(data):,} baris")


elif menu == "Upload Data Audit":
    st.title("📂 Upload Data Audit")
    st.write("Unggah data transaksi dalam format Excel (.xlsx) atau CSV (.csv).")
    uploaded_file = st.file_uploader(
        "Pilih file data audit",
        type=["xlsx", "xls", "csv"],
        help="Pastikan file memiliki baris judul kolom.",
    )
    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                uploaded_data = pd.read_csv(uploaded_file)
            else:
                uploaded_data = pd.read_excel(uploaded_file)

            if uploaded_data.empty:
                st.warning("File berhasil dibaca, tetapi tidak memiliki baris data.")
            else:
                st.session_state.data = uploaded_data
                st.session_state.file_name = uploaded_file.name
                st.session_state.fraud_data = None
                st.session_state.ai_result = None
                st.success("Data berhasil diunggah!")
                st.write(f"Nama file: **{uploaded_file.name}**")
                st.write(f"Ukuran data: **{uploaded_data.shape[0]} baris × {uploaded_data.shape[1]} kolom**")
                st.dataframe(uploaded_data.head(20), use_container_width=True)
        except Exception as exc:
            st.error(f"File tidak dapat dibaca: {exc}")

    if data is not None:
        st.divider()
        st.subheader("Data yang sedang digunakan")
        st.write(f"**{st.session_state.file_name}**")
        st.dataframe(data.head(10), use_container_width=True)


elif menu == "Informasi Data":
    st.title("📋 Informasi Data")
    if data is None:
        st.warning("Silakan unggah data terlebih dahulu melalui menu Upload Data Audit.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Jumlah Baris", f"{len(data):,}")
        c2.metric("Jumlah Kolom", f"{len(data.columns):,}")
        c3.metric("Data Kosong", f"{int(data.isna().sum().sum()):,}")

        st.subheader("Pratinjau Data")
        st.dataframe(data.head(20), use_container_width=True)

        st.subheader("Struktur Kolom")
        info_df = pd.DataFrame({
            "Nama Kolom": data.columns.astype(str),
            "Tipe Data": [str(x) for x in data.dtypes],
            "Jumlah Data Terisi": [int(data[c].notna().sum()) for c in data.columns],
            "Jumlah Data Kosong": [int(data[c].isna().sum()) for c in data.columns],
        })
        st.dataframe(info_df, use_container_width=True)

        st.subheader("Statistik Deskriptif")
        st.dataframe(data.describe(include="all").fillna(""), use_container_width=True)


elif menu == "Pemeriksaan Data Audit":
    st.title("🔎 Pemeriksaan Data Audit")
    if data is None:
        st.warning("Silakan unggah data terlebih dahulu.")
    else:
        missing_data = get_missing_data(data)
        duplicate_data = get_duplicate_data(data)
        outlier_data = get_outlier_data(data)

        a, b, c = st.columns(3)
        a.metric("Kolom dengan Data Kosong", len(missing_data))
        b.metric("Baris Duplikat", len(duplicate_data))
        c.metric("Baris dengan Nilai Tidak Biasa", outlier_data["Nomor Baris"].nunique() if not outlier_data.empty else 0)

        tab1, tab2, tab3, tab4 = st.tabs(
            ["Data Kosong", "Data Duplikat", "Outlier", "Debit dan Kredit"]
        )
        with tab1:
            st.subheader("Pemeriksaan Data Kosong")
            if missing_data.empty:
                st.success("Tidak ditemukan data kosong.")
            else:
                st.dataframe(missing_data, use_container_width=True)
        with tab2:
            st.subheader("Pemeriksaan Data Duplikat")
            if duplicate_data.empty:
                st.success("Tidak ditemukan baris duplikat.")
            else:
                st.dataframe(duplicate_data, use_container_width=True)
        with tab3:
            st.subheader("Pemeriksaan Nilai Tidak Biasa (IQR)")
            st.caption("Metode IQR merupakan penyaringan statistik awal, bukan bukti kesalahan.")
            if outlier_data.empty:
                st.success("Tidak ditemukan nilai di luar batas IQR.")
            else:
                st.dataframe(outlier_data, use_container_width=True)
        with tab4:
            st.subheader("Pemeriksaan Keseimbangan Debit dan Kredit")
            numeric_cols = get_numeric_columns(data)
            if len(numeric_cols) < 2:
                st.info("Data memerlukan minimal dua kolom numerik untuk pemeriksaan debit-kredit.")
            else:
                debit_col = st.selectbox("Pilih kolom Debit", numeric_cols, key="audit_debit")
                credit_options = [c for c in numeric_cols if c != debit_col]
                credit_col = st.selectbox("Pilih kolom Kredit", credit_options, key="audit_credit")
                debit_total, credit_total, difference = get_debit_credit_check(
                    data, debit_col, credit_col
                )
                x, y, z = st.columns(3)
                x.metric("Total Debit", format_number(debit_total))
                y.metric("Total Kredit", format_number(credit_total))
                z.metric("Selisih", format_number(difference))
                if abs(difference) <= 0.01:
                    st.success("Total debit dan kredit seimbang.")
                else:
                    st.warning("Total debit dan kredit belum seimbang. Periksa kembali data dan pemilihan kolom.")


elif menu == "Analisis Anggaran dan Realisasi":
    st.title("📊 Analisis Anggaran dan Realisasi")
    if data is None:
        st.warning("Silakan unggah data terlebih dahulu.")
    else:
        numeric_cols = get_numeric_columns(data)
        if len(numeric_cols) < 2:
            st.info("Data memerlukan minimal dua kolom numerik, yaitu anggaran dan realisasi.")
        else:
            budget_col = st.selectbox("Pilih kolom Anggaran", numeric_cols, key="budget_column")
            actual_options = [c for c in numeric_cols if c != budget_col]
            actual_col = st.selectbox("Pilih kolom Realisasi", actual_options, key="actual_column")

            budget_values = pd.to_numeric(data[budget_col], errors="coerce").fillna(0)
            actual_values = pd.to_numeric(data[actual_col], errors="coerce").fillna(0)
            comparison = pd.DataFrame({
                "Anggaran": budget_values,
                "Realisasi": actual_values,
            })
            comparison["Selisih"] = comparison["Realisasi"] - comparison["Anggaran"]
            comparison["Persentase Realisasi"] = comparison.apply(
                lambda row: (row["Realisasi"] / row["Anggaran"] * 100)
                if row["Anggaran"] != 0 else None,
                axis=1,
            )

            total_budget = budget_values.sum()
            total_actual = actual_values.sum()
            total_diff = total_actual - total_budget
            percentage = total_actual / total_budget * 100 if total_budget else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Anggaran", format_number(total_budget))
            m2.metric("Total Realisasi", format_number(total_actual))
            m3.metric("Realisasi (%)", f"{percentage:.2f}%")

            st.subheader("Perbandingan Anggaran dan Realisasi")
            chart_data = pd.DataFrame({
                "Jenis": ["Anggaran", "Realisasi"],
                "Nilai": [total_budget, total_actual],
            })
            fig = px.bar(chart_data, x="Jenis", y="Nilai", text_auto=".2s",
                         title="Total Anggaran dan Realisasi")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Rincian Perbandingan")
            st.dataframe(comparison, use_container_width=True)
            st.session_state.budget_result = comparison


elif menu == "Fraud Detection":
    st.title("🕵️ Fraud Detection")
    if data is None:
        st.warning("Silakan unggah data terlebih dahulu.")
    else:
        st.write(
            "Fitur ini menyaring transaksi yang memiliki pola tertentu untuk ditinjau auditor. "
            "Hasil penandaan bukan kesimpulan bahwa kecurangan telah terjadi."
        )
        fraud_data = get_fraud_detection(data)
        st.session_state.fraud_data = fraud_data
        flagged = len(fraud_data)
        st.metric("Jumlah Baris dengan Indikasi", flagged)
        if fraud_data.empty:
            st.success("Tidak ada transaksi yang ditandai oleh aturan pemeriksaan awal.")
        else:
            st.warning("Baris berikut perlu ditinjau lebih lanjut dengan dokumen pendukung.")
            st.dataframe(fraud_data, use_container_width=True)
            st.download_button(
                "⬇️ Download Hasil Fraud Detection (CSV)",
                data=fraud_data.to_csv(index=False).encode("utf-8-sig"),
                file_name="hasil_fraud_detection.csv",
                mime="text/csv",
            )
        st.caption(
            "Aturan awal: baris duplikat, nilai numerik yang berada di luar batas IQR, "
            "dan nilai negatif. Nilai negatif atau outlier dapat memiliki alasan yang sah."
        )


elif menu == "Risk Assessment":
    st.title("⚠️ Risk Assessment")
    if data is None:
        st.warning("Silakan unggah data terlebih dahulu.")
    else:
        missing_data = get_missing_data(data)
        duplicate_data = get_duplicate_data(data)
        outlier_data = get_outlier_data(data)
        fraud_data = get_fraud_detection(data)

        numeric_cols = get_numeric_columns(data)
        debit_col, credit_col = None, None
        if len(numeric_cols) >= 2:
            with st.expander("Pengaturan pemeriksaan debit dan kredit (opsional)"):
                use_debit_credit = st.checkbox("Sertakan pemeriksaan keseimbangan debit-kredit")
                if use_debit_credit:
                    debit_col = st.selectbox("Kolom Debit", numeric_cols, key="risk_debit")
                    credit_options = [c for c in numeric_cols if c != debit_col]
                    credit_col = st.selectbox("Kolom Kredit", credit_options, key="risk_credit")

        score, category, details = calculate_risk_assessment(
            data, fraud_data, missing_data, duplicate_data, outlier_data,
            debit_col, credit_col
        )
        st.metric("Skor Risiko Awal", f"{score}/100")
        if category == "Tinggi":
            st.error(f"Kategori Risiko: {category}")
        elif category == "Sedang":
            st.warning(f"Kategori Risiko: {category}")
        else:
            st.success(f"Kategori Risiko: {category}")
        st.progress(score / 100)

        st.subheader("Faktor yang Memengaruhi Penilaian")
        if details:
            for item in details:
                st.write(f"• {item}")
        else:
            st.write("Tidak ada faktor risiko yang ditandai oleh aturan pemeriksaan awal.")

        st.subheader("Rekomendasi Tindak Lanjut")
        if category == "Tinggi":
            st.write("Lakukan pemeriksaan lebih lanjut, telusuri dokumen sumber, dan verifikasi transaksi yang ditandai.")
        elif category == "Sedang":
            st.write("Periksa baris dan kolom yang ditandai, kemudian cocokkan dengan bukti transaksi.")
        else:
            st.write("Pertahankan pemeriksaan rutin dan pastikan kelengkapan dokumen pendukung.")
        st.caption(
            "Catatan: skor merupakan indikator heuristik sederhana untuk membantu prioritas pemeriksaan, "
            "bukan penilaian risiko yang tervalidasi atau pengganti pertimbangan auditor."
        )
        st.session_state.risk_result = (score, category, details)


elif menu == "Ringkasan Temuan Audit":
    st.title("📝 Ringkasan Temuan Audit")
    if data is None:
        st.warning("Silakan unggah data terlebih dahulu.")
    else:
        missing_data = get_missing_data(data)
        duplicate_data = get_duplicate_data(data)
        outlier_data = get_outlier_data(data)
        fraud_data = get_fraud_detection(data)
        score, category, details = calculate_risk_assessment(
            data, fraud_data, missing_data, duplicate_data, outlier_data
        )
        findings = build_findings(
            data, missing_data, duplicate_data, outlier_data, fraud_data, score, category
        )
        st.subheader("Hasil Pemeriksaan")
        for i, finding in enumerate(findings, start=1):
            st.write(f"**{i}.** {finding}")
        st.subheader("Tingkat Risiko Awal")
        st.metric("Skor Risiko", f"{score}/100", category)
        st.caption("Ringkasan ini dihasilkan berdasarkan aturan pemeriksaan awal aplikasi.")


elif menu == "AI Audit Analysis":
    st.title("🤖 AI Audit Analysis")
    if data is None:
        st.warning("Silakan unggah data terlebih dahulu.")
    else:
        st.write(
            "AI membantu menyusun analisis berdasarkan data yang diunggah dan hasil pemeriksaan. "
            "Hasil AI tetap perlu diverifikasi oleh auditor."
        )
        if st.button("✨ Mulai Analisis AI", type="primary"):
            with st.spinner("ADIWIA sedang menganalisis data..."):
                missing_data = get_missing_data(data)
                duplicate_data = get_duplicate_data(data)
                outlier_data = get_outlier_data(data)
                fraud_data = get_fraud_detection(data)
                score, category, details = calculate_risk_assessment(
                    data, fraud_data, missing_data, duplicate_data, outlier_data
                )
                findings = build_findings(
                    data, missing_data, duplicate_data, outlier_data, fraud_data, score, category
                )
                st.session_state.ai_result = generate_ai_analysis(data, findings)

        if st.session_state.ai_result:
            st.subheader("Hasil Analisis AI")
            st.markdown(st.session_state.ai_result)


elif menu == "Download Laporan Audit":
    st.title("📥 Download Laporan Audit")
    if data is None:
        st.warning("Silakan unggah data terlebih dahulu.")
    else:
        missing_data = get_missing_data(data)
        duplicate_data = get_duplicate_data(data)
        outlier_data = get_outlier_data(data)
        fraud_data = get_fraud_detection(data)
        score, category, details = calculate_risk_assessment(
            data, fraud_data, missing_data, duplicate_data, outlier_data
        )
        findings = build_findings(
            data, missing_data, duplicate_data, outlier_data, fraud_data, score, category
        )
        ai_result = st.session_state.ai_result or "Analisis AI belum dijalankan."
        budget_result = st.session_state.get("budget_result")

        st.write("Laporan Excel akan berisi data transaksi dan hasil pemeriksaan ADIWIA.")
        st.write("**Isi laporan:**")
        st.write(
            "Data Transaksi, Data Kosong, Data Duplikat, Data Outlier, Fraud Detection, "
            "Risk Assessment, Detail Risiko, Ringkasan Temuan, dan Analisis AI."
        )
        report = create_excel_report(
            data, missing_data, duplicate_data, outlier_data, fraud_data,
            score, category, details, findings, ai_result, budget_result
        )
        st.download_button(
            "📥 Download Laporan Audit Excel",
            data=report,
            file_name="Laporan_Audit_ADIWIA.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
        st.caption(
            "Pastikan hasil pemeriksaan dan analisis AI telah ditinjau sebelum laporan digunakan."
        )

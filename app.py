import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# ========================
# CONFIG & STYLE
# ========================
st.set_page_config(layout="wide", page_title="Financial Terminal")

CSS_STYLE = (
    "<style>"
    ".main { background-color: #000000; color: #ffffff; }"
    ".leader-box {"
    "    background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);"
    "    border: 1px solid #333;"
    "    border-radius: 8px;"
    "    padding: 15px;"
    "    margin-bottom: 12px;"
    "}"
    ".leader-ticker { color: #ff9900; font-size: 1.4em; font-weight: bold; }"
    ".leader-mom { color: #00ff00; font-family: monospace; }"
    ".rotation-box {"
    "    text-align:center;"
    "    padding:40px;"
    "    border-radius:12px;"
    "    font-size:32px;"
    "    font-weight:bold;"
    "}"
    ".vol-badge {"
    "    display: inline-flex;"
    "    align-items: center;"
    "    gap: 6px;"
    "    margin-top: 6px;"
    "    font-family: Courier New, monospace;"
    "    font-size: 0.85em;"
    "}"
    ".vol-square {"
    "    display: inline-flex;"
    "    align-items: center;"
    "    justify-content: center;"
    "    width: 18px;"
    "    height: 18px;"
    "    border-radius: 3px;"
    "    font-size: 11px;"
    "    font-weight: bold;"
    "    line-height: 1;"
    "}"
    ".vol-green  { background-color: #1a4a1a; border: 1.5px solid #00cc44; color: #00ff55; }"
    ".vol-red    { background-color: #4a1a1a; border: 1.5px solid #cc2200; color: #ff4422; }"
    ".vol-yellow { background-color: #3a3a00; border: 1.5px solid #aaaa00; color: #ffff44; }"
    ".vol-label-confirmed    { color: #00ff55; font-weight: bold; letter-spacing: 0.05em; }"
    ".vol-label-exhaustion   { color: #ffaa00; font-weight: bold; letter-spacing: 0.05em; }"
    ".vol-label-reversal     { color: #44aaff; font-weight: bold; letter-spacing: 0.05em; }"
    ".vol-label-distribution { color: #ff4422; font-weight: bold; letter-spacing: 0.05em; }"
    ".vol-label-neutral      { color: #aaaaaa; font-weight: bold; letter-spacing: 0.05em; }"
    ".vol-sublabel {"
    "    color: #666;"
    "    font-size: 0.78em;"
    "    margin-top: 2px;"
    "    font-style: italic;"
    "}"
    "</style>"
)
st.markdown(CSS_STYLE, unsafe_allow_html=True)

# ========================
# TICKERS
# ========================
SECTORS = ["XLK","XLY","XLF","XLC","XLV","XLP","XLI","XLE","XLB","XLU","XLRE"]
BENCHMARK = "SPY"
ALL_TICKERS = SECTORS + [BENCHMARK]

CYCLICAL = ["XLK","XLY","XLF","XLI","XLB","XLE"]
DEFENSIVE = ["XLV","XLP","XLU","XLRE"]

FACTOR_ETFS = [
    "MVOL.MI","IWQU.MI","IWMO.MI","IWVL.MI",
    "IUSN.DE","SWDA.MI","IQSA.MI"
]
FACTOR_COMPARISON = ["SWDA.MI","IQSA.MI"]

WEIGHTS = {"1M":0.30,"3M":0.40,"6M":0.30}

# ── ROS 2.0 weights (Intervento 1) ──────────────────────────────────────────
WEIGHTS_V2 = {"1W": 0.15, "1M": 0.25, "3M": 0.35, "6M": 0.25}

# ── Vol Confirmation score map (Intervento 3) ────────────────────────────────
VOL_SCORE_MAP = {
    "[B+M+] ACCUMULO":   +1.0,
    "[B+M-] INVERSIONE": +0.3,
    "[B~ M~] INDECISO":   0.0,
    "[B-M+] ESAURIM.":   -0.3,
    "[B-M-] DISTRIBUZ":  -1.0,
}

# ========================
# STRUTTURA ETF TEMATICI
# ========================
TEMATICI_STRUCT = [
    ("TECHNOLOGY",              ["BCHN.MI","XAIX.MI","QNTM.MI","CIBR.MI","ECAR.MI"],   "XDWT.DE"),
    ("CONS. DISCREZIONALI",     ["GLUX.MI","EXV5.DE","EXV9.DE","ECOM.MI"],              "XDWC.DE"),
    ("FINANCIALS",              ["ITBL.MI","BNKE.PA","EXH5.DE","DPAY.MI"],              "XDWF.DE"),
    ("COMM. SERVICE",           ["ESPO.MI","EXV2.DE","KWEB.AS"],                        "XWTS.DE"),
    ("HEALTHCARE",              ["AGED.MI","2B70.DE","DOCT.MI","HEAL.MI"],              "XDWH.DE"),
    ("CONSUMER STAPLES",        ["EXH3.DE","DXSK.DE"],                                  "XDWS.DE"),
    ("INDUSTRIAL",              ["HTWO.MI","DFNS.MI","JEDI.MI","XSGI.MI","PAVE.MI"],    "XDWI.DE"),
    ("BASIC MATERIALS",         ["REMX.MI","BATT.MI","EXV7.DE","ISAG.MI","WOOE.AS"],   "XDWM.DE"),
    ("ENERGY",                  ["STNX.MI","IOGP.AS","NUCL.MI"],                        "XDW0.DE"),
    ("UTILITIES",               ["H2OA.AS","INRG.MI","WNDY.DE","RENW.MI","SOLR.MI"],   "XDWU.DE"),
    ("IMMOBILIARE",             ["V9N.DE","IPRE.DE","IASP.AS","WTRE.MI"],               "EPRA.MI"),
    ("INTRAS./ALTERNATIVI",     ["ARKK.MI","WPAY.MI","UNIC.MI","GOAT.PA","FOOD.MI"],   "SWDA.MI"),
]

TEMATICI_DESCRIPTIONS = {
    "BCHN.MI": "blockchain & crypto", "XAIX.MI": "AI", "QNTM.MI": "quantum comp.",
    "CIBR.MI": "cybersecurity",       "ECAR.MI": "mobilità elettr.",
    "GLUX.MI": "beni di lusso",       "EXV5.DE": "automobili",
    "EXV9.DE": "travel & leisure",    "ECOM.MI": "e.commerce",
    "ITBL.MI": "banche italiane",     "BNKE.PA": "banche europa",   "EXH5.DE": "assic. europa",
    "ESPO.MI": "gaming",              "EXV2.DE": "telco europa",
    "AGED.MI": "ageing popul.",       "2B70.DE": "biotech",
    "DOCT.MI": "tech salute",         "HEAL.MI": "health innovat.",
    "EXH3.DE": "food & beverage",     "DXSK.DE": "cons.stapl.europa",
    "HTWO.MI": "idrogeno",            "DFNS.MI": "difesa",          "JEDI.MI": "aerospazio",
    "REMX.MI": "terre rare",          "BATT.MI": "batterie",
    "EXV7.DE": "chimica",             "ISAG.MI": "agricoltura",
    "STNX.MI": "energia europa",      "IOGP.AS": "oil & gas global","NUCL.MI": "nucleare",
    "H2OA.AS": "acqua",               "INRG.MI": "rinnovabili",
    "WNDY.DE": "eolico",              "RENW.MI": "rinnovabili (2)",
    "SOLR.MI": "energia solare",      "V9N.DE":  "imm. data cent.",
    "IPRE.DE": "imm. europa",         "IASP.AS": "imm. asia",
    "DPAY.MI": "pagamenti digitali",  "XSGI.MI": "infrast. globali",
    "WOOE.AS": "legname",             "WPAY.MI": "humanoid & drones",
    "UNIC.MI":"disruptive tech.",     "GOAT.PA": "global moat",     "FOOD.MI": "futuro del cibo",
}

ALL_THEMATIC_TICKERS = list(dict.fromkeys(
    t for _, tickers, bm in TEMATICI_STRUCT for t in tickers + [bm]
))

TF_DAYS = {"1D": 1, "1W": 5, "1M": 21, "3M": 63, "6M": 126, "YTD": None, "1A": 252, "2A": 504}

# ========================
# DATA LOADERS
# ========================
@st.cache_data(ttl=60*60)
def load_prices(tickers):
    end = datetime.today()
    start = end - timedelta(days=6*365)
    data = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False
    )
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"]
    else:
        close = data
    return close.dropna(how="all")


@st.cache_data(ttl=60*60)
def load_ohlcv(tickers):
    end = datetime.today()
    start = end - timedelta(days=90)
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False
    )
    return raw


WORLDPE_URLS = {
    "XLK":  "https://worldperatio.com/sector/sp-500-information-technology",
    "XLY":  "https://worldperatio.com/sector/sp-500-consumer-discretionary",
    "XLF":  "https://worldperatio.com/sector/sp-500-financials",
    "XLC":  "https://worldperatio.com/sector/sp-500-communication-services",
    "XLV":  "https://worldperatio.com/sector/sp-500-health-care",
    "XLP":  "https://worldperatio.com/sector/sp-500-consumer-staples",
    "XLI":  "https://worldperatio.com/sector/sp-500-industrials",
    "XLE":  "https://worldperatio.com/sector/sp-500-energy",
    "XLB":  "https://worldperatio.com/sector/sp-500-materials",
    "XLU":  "https://worldperatio.com/sector/sp-500-utilities",
    "XLRE": "https://worldperatio.com/sector/sp-500-real-estate",
}


@st.cache_data(ttl=60*60*6)
def load_pe_live_worldperatio(tickers):
    import requests
    import re
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    result  = {}
    _failed = []

    for ticker in tickers:
        url = WORLDPE_URLS.get(ticker)
        if not url:
            result[ticker] = None
            continue
        try:
            resp = requests.get(url, headers=headers, timeout=12)
            resp.raise_for_status()
            text = BeautifulSoup(resp.text, "html.parser").get_text()
            match = re.search(r"P/E Ratio\s*\n\s*([\d.]+)", text)
            if match:
                result[ticker] = float(match.group(1))
            else:
                result[ticker] = None
                _failed.append(ticker)
        except Exception:
            result[ticker] = None
            _failed.append(ticker)

    if _failed:
        for t in _failed:
            try:
                info = yf.Ticker(t).info
                pe = info.get("trailingPE") or info.get("forwardPE")
                result[t] = round(pe, 2) if pe else None
            except Exception:
                result[t] = None

    return result, _failed


@st.cache_data(ttl=60*60*12)
def load_pe_historical():
    try:
        pe_hist = pd.read_excel("pe_historical.xlsx", sheet_name="PE_Historical")
        return pe_hist.set_index("Period")
    except FileNotFoundError:
        return None
    except Exception:
        return None


@st.cache_data(ttl=60*60*6)
def load_sp500_data(timeframe_days: int):
    import requests
    from io import StringIO

    wiki = None

    # Tentativo 1 — Wikipedia con StringIO (evita il parsing diretto di resp.text)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers=headers, timeout=15
        )
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text), attrs={"id": "constituents"})
        if tables:
            raw = tables[0]
            # colonne possibili a seconda della versione Wikipedia
            sym_col  = next((c for c in raw.columns if "Symbol"  in str(c) or "Ticker" in str(c)), None)
            sec_col  = next((c for c in raw.columns if "Sector"  in str(c) or "GICS"   in str(c)), None)
            if sym_col and sec_col:
                wiki = raw[[sym_col, sec_col]].copy()
                wiki.columns = ["Ticker", "Sector"]
                wiki["Ticker"] = wiki["Ticker"].str.replace(".", "-", regex=False)
    except Exception:
        pass

    # Tentativo 2 — fallback su primo table se constituents non trovato
    if wiki is None:
        try:
            tables = pd.read_html(StringIO(resp.text), header=0)
            raw = tables[0]
            sym_col = next((c for c in raw.columns if "Symbol" in str(c) or "Ticker" in str(c)), raw.columns[0])
            sec_col = next((c for c in raw.columns if "Sector" in str(c) or "GICS"   in str(c)), raw.columns[3])
            wiki = raw[[sym_col, sec_col]].copy()
            wiki.columns = ["Ticker", "Sector"]
            wiki["Ticker"] = wiki["Ticker"].astype(str).str.replace(".", "-", regex=False)
        except Exception as e:
            st.error(f"Errore caricamento lista S&P 500: {e}")
            return pd.DataFrame()

    if wiki is None or wiki.empty:
        st.error("Lista S&P 500 non disponibile. Riprova tra qualche minuto.")
        return pd.DataFrame()

    tickers = wiki["Ticker"].tolist()
    fetch_days = timeframe_days + 15
    end   = datetime.today()
    start = end - timedelta(days=fetch_days)

    try:
        raw = yf.download(
            tickers,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
            threads=True
        )
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
        else:
            close = raw
    except Exception as e:
        st.error(f"Errore yfinance: {e}")
        return pd.DataFrame()

    results = []
    for ticker in tickers:
        if ticker not in close.columns:
            continue
        series = close[ticker].dropna()
        if len(series) < 2:
            continue
        idx = min(timeframe_days, len(series) - 1)
        ret_val = (series.iloc[-1] / series.iloc[-idx] - 1) * 100
        results.append({"Ticker": ticker, "Return": round(ret_val, 2)})

    ret_df = pd.DataFrame(results)
    merged = ret_df.merge(wiki, on="Ticker", how="left")
    merged = merged.dropna(subset=["Sector"])
    return merged


@st.cache_data(ttl=60*60)
def load_thematic_prices():
    end   = datetime.today()
    start = end - timedelta(days=2*365 + 30)
    raw = yf.download(
        ALL_THEMATIC_TICKERS,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False
    )
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw
    return close.dropna(how="all")


# ========================
# VOLUME SIGNAL
# ========================
def compute_vwds(ohlcv_raw, ticker, window, w_dir=0.60, w_pos=0.40):
    try:
        if isinstance(ohlcv_raw.columns, pd.MultiIndex):
            hi = ohlcv_raw["High"][ticker].dropna()
            lo = ohlcv_raw["Low"][ticker].dropna()
            cl = ohlcv_raw["Close"][ticker].dropna()
            vo = ohlcv_raw["Volume"][ticker].dropna()
        else:
            hi = ohlcv_raw["High"].dropna()
            lo = ohlcv_raw["Low"].dropna()
            cl = ohlcv_raw["Close"].dropna()
            vo = ohlcv_raw["Volume"].dropna()

        idx = (hi.index
               .intersection(lo.index)
               .intersection(cl.index)
               .intersection(vo.index))
        hi, lo, cl, vo = hi[idx], lo[idx], cl[idx], vo[idx]
        hi = hi.iloc[-window:]
        lo = lo.iloc[-window:]
        cl = cl.iloc[-window:]
        vo = vo.iloc[-window:]

        if len(cl) < max(3, window // 3):
            return np.nan

        prev_cl   = cl.shift(1)
        pct_chg   = (cl - prev_cl) / prev_cl.replace(0, np.nan)
        direction = np.sign(cl - prev_cl)
        strength  = pct_chg.abs().clip(upper=0.05)
        dir_signal = direction * strength

        max_strength = strength.max()
        if pd.isna(max_strength) or max_strength == 0:
            dir_signal_norm = pd.Series(0.0, index=dir_signal.index)
        else:
            dir_signal_norm = (dir_signal / max_strength).fillna(0.0)

        buy_vol_dir  = vo * dir_signal_norm.clip(lower=0)
        sell_vol_dir = vo * dir_signal_norm.clip(upper=0).abs()

        rng = (hi - lo).replace(0, np.nan)
        pos_ratio = ((cl - lo) / rng).fillna(0.5).clip(0, 1)
        pos_signal = (pos_ratio - 0.5) * 2

        buy_vol_pos  = vo * pos_signal.clip(lower=0)
        sell_vol_pos = vo * pos_signal.clip(upper=0).abs()

        buy_total  = (w_dir * buy_vol_dir  + w_pos * buy_vol_pos).sum()
        sell_total = (w_dir * sell_vol_dir + w_pos * sell_vol_pos).sum()

        total = buy_total + sell_total
        if total == 0 or pd.isna(total):
            return np.nan

        score = (buy_total - sell_total) / total
        return round(float(score), 3)

    except Exception:
        return np.nan


def volume_signal(score_short, score_medium):
    THRESHOLD = 0.05

    def is_pos(s): return s is not None and not np.isnan(s) and s >  THRESHOLD
    def is_neg(s): return s is not None and not np.isnan(s) and s < -THRESHOLD

    sq_green  = '<span class="vol-square vol-green">✓</span>'
    sq_red    = '<span class="vol-square vol-red">✗</span>'
    sq_yellow = '<span class="vol-square vol-yellow">~</span>'

    sq_s = sq_green if is_pos(score_short) else sq_red if is_neg(score_short) else sq_yellow
    sq_m = sq_green if is_pos(score_medium) else sq_red if is_neg(score_medium) else sq_yellow

    if is_pos(score_short) and is_pos(score_medium):
        label, css_label = "CONFERMATO",      "vol-label-confirmed"
        sublabel, text_plain = "Volume in accumulo su entrambi i timeframe", "[B+M+] ACCUMULO"
    elif is_neg(score_short) and is_neg(score_medium):
        label, css_label = "DISTRIBUZIONE",   "vol-label-distribution"
        sublabel, text_plain = "Pressione vendita dominante — cautela", "[B-M-] DISTRIBUZ"
    elif is_pos(score_short) and is_neg(score_medium):
        label, css_label = "INVERSIONE IN CORSO", "vol-label-reversal"
        sublabel, text_plain = "Breve si rafforza su medio debole — monitorare", "[B+M-] INVERSIONE"
    elif is_neg(score_short) and is_pos(score_medium):
        label, css_label = "ESAURIMENTO",     "vol-label-exhaustion"
        sublabel, text_plain = "Breve si deteriora su medio positivo — attenzione", "[B-M+] ESAURIM."
    else:
        label, css_label = "INDECISO",        "vol-label-neutral"
        sublabel, text_plain = "Segnale volumetrico non direzionale", "[B~ M~] INDECISO"

    html_badge = (
        f'{sq_s}&nbsp;{sq_m}&nbsp;'
        f'<span class="{css_label}">{label}</span>'
        f'<br><span class="vol-sublabel">{sublabel}</span>'
    )
    return html_badge, text_plain
# ========================
# ENHANCED OBV FLOW
# ========================
def compute_obv_flow(close: pd.Series, volume: pd.Series,
                     len_vol: int = 20, len_ema: int = 13,
                     len_cci: int = 20, len_trend: int = 50) -> dict:
    """
    Traduzione Python di Enhanced OBV Flow v2.3 (Pine Script).
    Parametri validati:
      Daily:  len_vol=20, len_ema=13, len_cci=20, len_trend=50
      Weekly: len_vol=10, len_ema=8,  len_cci=14, len_trend=30

    Ritorna dict con serie temporali:
      flow_cum   : flow cumulato normalizzato
      flow_ema   : EMA del flow (cuore dell'indicatore)
      flow_trend : SMA di lungo periodo (filtro regime)
      cci_flow   : CCI calcolato su flow_ema
      cci_scaled : CCI riproiettato sulla scala del flow (momentum visivo)
    """
    close  = close.dropna()
    volume = volume.dropna()
    idx    = close.index.intersection(volume.index)
    close  = close[idx]
    volume = volume[idx]

    if len(close) < max(len_vol, len_trend) + 5:
        empty = pd.Series(dtype=float)
        return {k: empty for k in
                ["flow_cum","flow_ema","flow_trend","cci_flow","cci_scaled"]}

    # 1. Normalizzazione volume
    avg_vol  = volume.rolling(len_vol, min_periods=len_vol // 2).mean()
    norm_vol = volume / avg_vol.replace(0, np.nan)

    # 2. Flow cumulato
    chg      = close.diff()
    direction = np.sign(chg).fillna(0)
    flow_cum  = (direction * norm_vol).fillna(0).cumsum()

    # 3. Flow EMA (smoothing strutturale)
    flow_ema = flow_cum.ewm(span=len_ema, adjust=False).mean()

    # 4. Trend filter SMA
    flow_trend = flow_ema.rolling(len_trend, min_periods=len_trend // 2).mean()

    # 5. CCI su flow_ema
    flow_ema_sma = flow_ema.rolling(len_cci, min_periods=len_cci // 2).mean()
    flow_ema_std = flow_ema.rolling(len_cci, min_periods=len_cci // 2).std()
    # Mean deviation per CCI (Pine usa mean deviation, non std)
    mean_dev = flow_ema.rolling(len_cci, min_periods=len_cci // 2).apply(
        lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
    ).replace(0, np.nan)
    cci_flow = (flow_ema - flow_ema_sma) / (0.015 * mean_dev)

    # 6. CCI rescalato su scala flow (z-score -> proiezione su flow_std)
    cci_sma   = cci_flow.rolling(len_cci, min_periods=len_cci // 2).mean()
    cci_std   = cci_flow.rolling(len_cci, min_periods=len_cci // 2).std().replace(0, np.nan)
    cci_z     = (cci_flow - cci_sma) / cci_std
    flow_mid  = flow_ema_sma
    flow_std  = flow_ema_std.replace(0, np.nan)
    cci_scaled = flow_mid + cci_z * flow_std * 0.5

    return {
        "flow_cum"   : flow_cum,
        "flow_ema"   : flow_ema,
        "flow_trend" : flow_trend,
        "cci_flow"   : cci_flow,
        "cci_scaled" : cci_scaled,
    }


def obv_flow_regime(close: pd.Series, volume: pd.Series,
                    len_vol: int = 20, len_ema: int = 13,
                    len_cci: int = 20, len_trend: int = 50) -> str:
    """
    Ritorna stringa regime corrente per uso in tabella:
    'BULL FLOW', 'BEAR FLOW', o 'N/D'
    """
    result = compute_obv_flow(close, volume, len_vol, len_ema, len_cci, len_trend)
    fe = result["flow_ema"]
    ft = result["flow_trend"]
    if fe.empty or ft.empty:
        return "N/D"
    last_fe = fe.dropna()
    last_ft = ft.dropna()
    if last_fe.empty or last_ft.empty:
        return "N/D"
    common = last_fe.index.intersection(last_ft.index)
    if len(common) == 0:
        return "N/D"
    return "BULL FLOW" if float(last_fe[common[-1]]) > float(last_ft[common[-1]]) else "BEAR FLOW"


# ========================
# RETURN FUNCTIONS
# ========================
def ret(data, days):
    if len(data) <= days:
        return np.nan
    return (data.iloc[-1] / data.iloc[-days-1] - 1) * 100

def ret_ytd(data):
    ytd = data[data.index.year == datetime.today().year]
    if len(ytd) < 2:
        return np.nan
    return (ytd.iloc[-1] / ytd.iloc[0] - 1) * 100

def rsr(asset_ret, benchmark_ret):
    return ((1 + asset_ret/100) / (1 + benchmark_ret/100) - 1) * 100

def safe_ret(series, days):
    try:
        s = series.dropna()
        if days is None:
            ytd = s[s.index.year == datetime.today().year]
            if len(ytd) < 2:
                return np.nan
            return float((ytd.iloc[-1] / ytd.iloc[0] - 1) * 100)
        if len(s) <= days:
            return np.nan
        return float((s.iloc[-1] / s.iloc[-days - 1] - 1) * 100)
    except Exception:
        return np.nan


# ========================
# ROTATION SCORE — v1 (originale, usata in Tab8/Backtest)
# ========================
def compute_rotation_score_series(prices):
    ret_1m = prices.pct_change(21, fill_method=None)
    ret_3m = prices.pct_change(63, fill_method=None)
    ret_6m = prices.pct_change(126, fill_method=None)

    rar_1m = ret_1m.sub(ret_1m[BENCHMARK], axis=0)
    rar_3m = ret_3m.sub(ret_3m[BENCHMARK], axis=0)
    rar_6m = ret_6m.sub(ret_6m[BENCHMARK], axis=0)

    rar_mean = (rar_1m + rar_3m + rar_6m) / 3
    cyc  = rar_mean[CYCLICAL].mean(axis=1)
    def_ = rar_mean[DEFENSIVE].mean(axis=1)
    rotation_score = (cyc - def_) * 100
    return rotation_score.dropna()


# ========================
# ROTATION SCORE — v2 (ROS 2.0, Intervento 1)
# ========================
def compute_rotation_score_series_v2(prices):
    """
    ROS 2.0 — momentum relativo multi-timeframe con leading edge 1W.
    Pesi: 1W=15% · 1M=25% · 3M=35% · 6M=25%
    """
    ret_1w  = prices.pct_change(5,   fill_method=None)
    ret_1m  = prices.pct_change(21,  fill_method=None)
    ret_3m  = prices.pct_change(63,  fill_method=None)
    ret_6m  = prices.pct_change(126, fill_method=None)

    rar_1w = ret_1w.sub(ret_1w[BENCHMARK], axis=0)
    rar_1m = ret_1m.sub(ret_1m[BENCHMARK], axis=0)
    rar_3m = ret_3m.sub(ret_3m[BENCHMARK], axis=0)
    rar_6m = ret_6m.sub(ret_6m[BENCHMARK], axis=0)

    rar_weighted = (
        rar_1w * WEIGHTS_V2["1W"] +
        rar_1m * WEIGHTS_V2["1M"] +
        rar_3m * WEIGHTS_V2["3M"] +
        rar_6m * WEIGHTS_V2["6M"]
    )

    cyc  = rar_weighted[CYCLICAL].mean(axis=1)
    def_ = rar_weighted[DEFENSIVE].mean(axis=1)
    return (cyc - def_) * 100


# ========================
# ADAPTIVE THRESHOLD — Intervento 2
# ========================
def compute_adaptive_threshold(series, window=252, multiplier=0.75):
    """
    Soglia adattiva basata su rolling std a 252 giorni.
    In laterale si restringe, in trend si allarga.
    """
    rolling_std = series.rolling(window=window, min_periods=63).std()
    return (rolling_std * multiplier).dropna()


# ========================
# VOL CONFIRMATION — Intervento 3
# ========================
def compute_vol_confirmation(vol_plain_dict, cyclicals, defensives):
    """
    Vol Confirmation Score: media vol ciclici − media vol difensivi.
    Range teorico [-2, +2]. Positivo = volume conferma risk-on.
    """
    cyc_scores = [
        VOL_SCORE_MAP.get(vol_plain_dict.get(t, "[B~ M~] INDECISO"), 0.0)
        for t in cyclicals
    ]
    def_scores = [
        VOL_SCORE_MAP.get(vol_plain_dict.get(t, "[B~ M~] INDECISO"), 0.0)
        for t in defensives
    ]
    cyc_mean = float(np.mean(cyc_scores)) if cyc_scores else 0.0
    def_mean = float(np.mean(def_scores)) if def_scores else 0.0
    return round(cyc_mean - def_mean, 3)


def compute_vol_multiplier(vol_confirmation):
    """
    Traduce il Vol Confirmation Score in moltiplicatore scalare.
    >= +0.5 → 1.0 (pieno) · [0, 0.5) → 0.75 (parziale) · < 0 → 0.5 (dimezzato)
    """
    if vol_confirmation >= 0.5:
        return 1.0
    elif vol_confirmation >= 0.0:
        return 0.75
    else:
        return 0.5


# ========================
# INT.4 — DERIVATA BANDA ADATTIVA
# ========================
def compute_band_derivative(adaptive_threshold_series, window=10):
    if adaptive_threshold_series.empty or len(adaptive_threshold_series) < window + 2:
        return pd.Series(dtype=float), {
            "deriv": float('nan'), "stato": "N/D", "color": "#888888",
            "soglia_stretta": float('nan'), "soglia_larga": float('nan'), "deriv_std": float('nan'),
        }
    deriv     = adaptive_threshold_series.pct_change(window).dropna() * 100
    deriv_std = float(deriv.std())
    s_str     = -0.5 * deriv_std
    s_lar     =  0.5 * deriv_std
    deriv_now = float(deriv.iloc[-1]) if not deriv.empty else float('nan')
    import math
    if math.isnan(deriv_now):
        stato, color = "N/D", "#888888"
    elif deriv_now < s_str * 2:
        stato, color = "STRETTA RAPIDA", "#ff4422"
    elif deriv_now < s_str:
        stato, color = "STRETTA", "#ffaa00"
    elif deriv_now > s_lar * 2:
        stato, color = "LARGA RAPIDA", "#44aaff"
    elif deriv_now > s_lar:
        stato, color = "LARGA", "#888888"
    else:
        stato, color = "STABILE", "#aaaaaa"
    return deriv, {
        "deriv": deriv_now, "stato": stato, "color": color,
        "soglia_stretta": s_str, "soglia_larga": s_lar, "deriv_std": deriv_std,
    }


# ========================
# RISK OFF EPISODES
# ========================
def compute_risk_off_episodes(series, threshold, confirm_days=3):
    if series.empty:
        return []

    neg_threshold = -abs(threshold)
    episodes = []
    in_episode   = False
    ep_start     = None
    ep_confirmed = None
    consec_below = 0
    consec_above = 0

    for date, val in series.items():
        is_below = val < neg_threshold

        if not in_episode:
            if is_below:
                consec_below += 1
                if consec_below == 1:
                    ep_start = date
                if consec_below >= confirm_days:
                    in_episode   = True
                    ep_confirmed = date
                    consec_above = 0
            else:
                consec_below = 0
                ep_start     = None
        else:
            if not is_below:
                consec_above += 1
                if consec_above >= confirm_days:
                    ep_slice = series[ep_start:date]
                    episodes.append({
                        "start":       ep_start,
                        "confirmed":   ep_confirmed,
                        "end":         date,
                        "open":        False,
                        "duration":    (date - ep_start).days,
                        "rs_min":      round(float(ep_slice.min()), 2),
                        "rs_min_date": ep_slice.idxmin(),
                    })
                    in_episode   = False
                    consec_below = 0
                    consec_above = 0
                    ep_start     = None
            else:
                consec_above = 0

    if in_episode and ep_start is not None:
        last_date = series.index[-1]
        ep_slice  = series[ep_start:]
        episodes.append({
            "start":       ep_start,
            "confirmed":   ep_confirmed,
            "end":         None,
            "open":        True,
            "duration":    (last_date - ep_start).days,
            "rs_min":      round(float(ep_slice.min()), 2),
            "rs_min_date": ep_slice.idxmin(),
        })

    return episodes


# ========================
# LOAD SECTORAL DATA
# ========================
prices = load_prices(ALL_TICKERS)
ohlcv  = load_ohlcv(ALL_TICKERS)

returns = pd.DataFrame({
    "1D": prices.apply(lambda x: ret(x, 1)),
    "1W": prices.apply(lambda x: ret(x, 5)),
    "1M": prices.apply(lambda x: ret(x, 21)),
    "3M": prices.apply(lambda x: ret(x, 63)),
    "6M": prices.apply(lambda x: ret(x, 126)),
})

rsr_df = pd.DataFrame(index=returns.index, columns=returns.columns)
for col in returns.columns:
    rsr_df[col] = rsr(returns[col], returns.loc[BENCHMARK, col])

df = rsr_df.loc[SECTORS].copy()
df["Rsr_momentum"] = (
    df["1M"] * WEIGHTS["1M"] +
    df["3M"] * WEIGHTS["3M"] +
    df["6M"] * WEIGHTS["6M"]
)
df["Coerenza_Trend"] = df[["1D","1W","1M","3M","6M"]].gt(0).sum(axis=1)
df["Delta_RS_5D"]    = df["1W"]
df = df.sort_values("Rsr_momentum", ascending=False)
df["Classifica"]     = range(1, len(df)+1)

def situazione(row):
    if row.Rsr_momentum > 0:
        return "LEADER" if row.Coerenza_Trend >= 4 else "IN RECUPERO"
    return "DEBOLE"

df["Situazione"] = df.apply(situazione, axis=1)

def operativita(row):
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4 and row["Delta_RS_5D"] > 0:
        return "🔥 LEADER"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4:
        return "📈 HOLD"
    if row["Classifica"] > 3 and row["Coerenza_Trend"] >= 4:
        return "👀 OSSERVARE"
    return "❌ EVITARE"

df["Operatività"] = df.apply(operativita, axis=1)

# ========================
# VOLUME SIGNAL
# ========================
vol_html  = {}
vol_plain = {}
_vol_errors = []
for ticker in SECTORS + [BENCHMARK]:
    s_short  = compute_vwds(ohlcv, ticker, window=10)
    s_medium = compute_vwds(ohlcv, ticker, window=20)
    if np.isnan(s_short) and np.isnan(s_medium):
        _vol_errors.append(ticker)
    h, p = volume_signal(s_short, s_medium)
    vol_html[ticker]  = h
    vol_plain[ticker] = p

if _vol_errors:
    st.sidebar.warning(
        f"⚠️ Volume Signal non disponibile per: {', '.join(_vol_errors)}. "
        "Dati OHLCV insufficienti o ticker non disponibile su Yahoo Finance."
    )

df["Vol Signal"] = df.index.map(vol_plain)
# ── OBV Flow Regime per Tab 1 ────────────────────────────────────────────
@st.cache_data(ttl=1)
def load_ohlcv_long(tickers):
    end   = datetime.today()
    start = end - timedelta(days=2*365)
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False
    )
    return raw

ohlcv_long = load_ohlcv_long(tuple(ALL_TICKERS))
obv_regime = {}
_obv_available = list(ohlcv_long["Close"].columns) if isinstance(ohlcv_long.columns, pd.MultiIndex) else [BENCHMARK]

for ticker in SECTORS + [BENCHMARK]:
    if ticker not in _obv_available:
        obv_regime[ticker] = "N/D"
        continue
    try:
        cl = ohlcv_long["Close"][ticker].dropna()
        vo = ohlcv_long["Volume"][ticker].dropna()
        if len(cl) < 60 or len(vo) < 60:
            obv_regime[ticker] = "N/D"
            continue
        obv_regime[ticker] = obv_flow_regime(cl, vo)
    except Exception as e:
        obv_regime[ticker] = "N/D"

df["Flow Regime"] = df.index.map(obv_regime)


# ========================
# UI TABS
# ========================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Dashboard Settoriale",
    "📈 Andamento Settoriale",
    "📊 Fattori",
    "🔄 Rotazione Settoriale",
    "🫧 S&P 500 Bubble",
    "📐 Valutazione P/E",
    "📌 Tematici",
    "🧪 Backtest RS",
])

# ========================
# TAB 1 — DASHBOARD
# ========================
with tab1:
    col1, col2 = st.columns([1.2, 1])

    with col1:
        colors = [
            '#FF6B6B','#4ECDC4','#45B7D1','#FFA07A',
            '#98D8C8','#F7DC6F','#BB8FCE','#85C1E2',
            '#F8B739','#52B788','#E76F51','#00FF00'
        ]
        tickers_list = ALL_TICKERS
        values       = [returns.loc[t, "1D"] for t in tickers_list]
        bar_colors   = [colors[i] for i in range(len(tickers_list))]

        fig = go.Figure(data=[
            go.Bar(
                x=tickers_list,
                y=values,
                marker=dict(color=bar_colors, line=dict(color='#333', width=1)),
                width=0.7,
                showlegend=False
            )
        ])
        fig.update_layout(
            height=420,
            paper_bgcolor="#000",
            plot_bgcolor="#000",
            font=dict(color="white", size=12),
            title=dict(text="Variazione % Giornaliera", font=dict(size=16, color="#ff9900")),
            xaxis=dict(tickangle=0, gridcolor="#1a1a1a"),
            yaxis=dict(
                title="",
                gridcolor="#1a1a1a",
                zeroline=True,
                zerolinecolor="#444",
                zerolinewidth=2
            ),
            margin=dict(l=40, r=20, t=50, b=40),
            bargap=0.15
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        for t, row in df.head(3).iterrows():
            badge   = vol_html[t]
            regime  = obv_regime.get(t, "N/D")
            reg_color = "#00ff55" if regime == "BULL FLOW" else "#ff4422" if regime == "BEAR FLOW" else "#888"
            html = (
                '<div class="leader-box">'
                f'<div class="leader-ticker">{t}</div>'
                f'<div class="leader-mom">RSR: {row.Rsr_momentum:.2f} &nbsp;|&nbsp; {row.Operatività} &nbsp;|&nbsp; {row.Situazione}</div>'
                f'<div style="margin-top:4px;font-size:0.80em;">'
                f'<span style="color:#555;letter-spacing:0.06em;font-size:0.85em;">FLOW REGIME &nbsp;</span>'
                f'<span style="color:{reg_color};font-weight:bold;font-family:monospace;">{regime}</span>'
                f'</div>'
                f'<div style="margin-top:5px;font-size:0.78em;color:#555;letter-spacing:0.06em;">VOL SIGNAL</div>'
                f'<div style="font-size:0.88em;margin-top:2px;">{badge}</div>'
                '</div>'
            )
            st.markdown(html, unsafe_allow_html=True)

    st.markdown(
        '<style>div[data-testid="stDataFrame"] { margin-top: -1rem; }</style>',
        unsafe_allow_html=True
    )

    def style_vol(val):
        v = str(val)
        if "ACCUMULO"   in v: return "background-color:#0d2b0d; color:#00ff55; font-weight:bold"
        if "DISTRIBUZ"  in v: return "background-color:#2b0d0d; color:#ff4422; font-weight:bold"
        if "ESAURIM"    in v: return "background-color:#2b1a00; color:#ffaa00; font-weight:bold"
        if "INVERSIONE" in v: return "background-color:#0d1a2b; color:#44aaff; font-weight:bold"
        if "INDECISO"   in v: return "background-color:#1a1a1a; color:#888888"
        return ""

    def style_flow_regime(val):
        v = str(val)
        if v == "BULL FLOW": return "background-color:#0d2b0d; color:#00ff55; font-weight:bold"
        if v == "BEAR FLOW": return "background-color:#2b0d0d; color:#ff4422; font-weight:bold"
        return "color:#888888"

    styled = (
        df.round(2)
        .style
        .map(style_vol,         subset=["Vol Signal"])
        .map(style_flow_regime, subset=["Flow Regime"])
    )

    st.dataframe(
        styled,
        width="stretch",
        column_config={
            "Vol Signal":   st.column_config.TextColumn("Vol Signal",   width="medium"),
            "Flow Regime":  st.column_config.TextColumn("Flow Regime",  width="small"),
        }
    )

    st.markdown("""
    <div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;
                padding:12px 20px;margin-top:8px;font-size:0.82em;color:#888;
                display:flex;gap:24px;flex-wrap:wrap;">
        <span><b style="color:#00ff55">[B+M+] ACCUMULO</b> — breve e medio positivi</span>
        <span><b style="color:#ffaa00">[B-M+] ESAURIM.</b> — breve si deteriora su medio positivo</span>
        <span><b style="color:#44aaff">[B+M-] INVERSIONE</b> — breve si rafforza su medio debole</span>
        <span><b style="color:#ff4422">[B-M-] DISTRIBUZ</b> — pressione vendita dominante</span>
        <span><b style="color:#888">[B~ M~] INDECISO</b> — segnale non direzionale</span>
        <span><b style="color:#00ff55">BULL FLOW</b> / <b style="color:#ff4422">BEAR FLOW</b> — flowEMA vs flowTrend (OBV normalizzato, Daily 20/13/50)</span>
    </div>
    """, unsafe_allow_html=True)

# ========================
# TAB 2 — ANDAMENTO
# ========================
with tab2:
    selected = st.multiselect("ETF", SECTORS, default=SECTORS)
    tf = st.selectbox("Timeframe", ["1W","1M","3M","6M","1Y","3Y","5Y"])

    days   = {"1W":5,"1M":21,"3M":63,"6M":126,"1Y":252,"3Y":756,"5Y":1260}[tf]
    slice_ = prices.iloc[-days:]
    norm   = (slice_ / slice_.iloc[0] - 1) * 100

    fig = go.Figure()
    for t in selected:
        fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=t))
    fig.add_trace(go.Scatter(
        x=norm.index, y=norm[BENCHMARK],
        name="SPY", line=dict(width=4, color="#00FF00")
    ))
    fig.update_layout(
        paper_bgcolor="#000",
        plot_bgcolor="#000",
        font_color="white",
        yaxis_title="Variazione %"
    )
    st.plotly_chart(fig, width="stretch")


# ========================
# TAB 3 — FATTORI
# ========================
with tab3:
    factor_prices = load_prices(FACTOR_ETFS)

    if factor_prices.empty or factor_prices.isna().all().all():
        st.error("⚠️ Impossibile scaricare i dati degli ETF fattoriali da Yahoo Finance.")
        st.info("Ticker richiesti: " + ", ".join(FACTOR_ETFS))
    else:
        f = pd.DataFrame(index=FACTOR_ETFS)
        f["Prezzo"] = factor_prices.iloc[-1].round(2)
        f["1D"]  = factor_prices.apply(lambda x: ret(x, 1))
        f["1W"]  = factor_prices.apply(lambda x: ret(x, 5))
        f["1M"]  = factor_prices.apply(lambda x: ret(x, 21))
        f["3M"]  = factor_prices.apply(lambda x: ret(x, 63))
        f["6M"]  = factor_prices.apply(lambda x: ret(x, 126))
        f["1A"]  = factor_prices.apply(lambda x: ret(x, 252))
        f["YTD"] = factor_prices.apply(ret_ytd)
        f["3A"]  = factor_prices.apply(lambda x: ret(x, 756))
        f["5A"]  = factor_prices.apply(lambda x: ret(x, 1260))

        def style_row(row):
            if row.name in FACTOR_COMPARISON:
                return ["background-color:#1e1e1e;color:#ccc"] * len(row)
            return ["background-color:#000;color:white"] * len(row)

        def highlight_extremes(s):
            valid = s.dropna()
            if valid.empty:
                return [""] * len(s)
            max_val = valid.max()
            min_val = valid.min()
            return [
                "background-color:#003300;color:#00FF00;font-weight:bold" if v == max_val
                else "background-color:#330000;color:#ff4422;font-weight:bold" if v == min_val
                else ""
                for v in s
            ]

        st.dataframe(
            f.round(2)
            .style
            .apply(style_row, axis=1)
            .apply(highlight_extremes, subset=[c for c in f.columns if c != "Prezzo"])
            .format({"Prezzo": "{:.2f}", **{c: "{:+.2f}%" for c in f.columns if c != "Prezzo"}}),
            width="stretch"
        )


# ========================
# TAB 4 — ROTAZIONE SETTORIALE v2
# ========================
with tab4:

    CYCLICALS  = ["XLK","XLY","XLF","XLI","XLE","XLB"]
    DEFENSIVES = ["XLP","XLV","XLU","XLRE"]

    # ── ROS v1 scalar (vecchio, per confronto numerico) ──────────────
    rar_focus_v1     = rsr_df[["1M","3M","6M"]].mean(axis=1)
    rotation_score_v1 = (
        rar_focus_v1.loc[CYCLICALS].mean() - rar_focus_v1.loc[DEFENSIVES].mean()
    )

    # ── ROS v2 scalar (Intervento 1) ─────────────────────────────────
    rar_weighted_scalar = (
        rsr_df["1W"] * WEIGHTS_V2["1W"] +
        rsr_df["1M"] * WEIGHTS_V2["1M"] +
        rsr_df["3M"] * WEIGHTS_V2["3M"] +
        rsr_df["6M"] * WEIGHTS_V2["6M"]
    )
    rotation_score_v2_scalar = (
        rar_weighted_scalar.loc[CYCLICALS].mean() -
        rar_weighted_scalar.loc[DEFENSIVES].mean()
    )

    # ── Intervento 3 — Vol Confirmation ──────────────────────────────
    vol_conf  = compute_vol_confirmation(vol_plain, CYCLICALS, DEFENSIVES)
    vol_mult  = compute_vol_multiplier(vol_conf)
    rotation_score_adjusted = rotation_score_v2_scalar * vol_mult

    # ── Serie storiche + Int.4 (anticipate per il 4 box header) ─────
    rotation_series_v1        = compute_rotation_score_series(prices)
    rotation_series_v2        = compute_rotation_score_series_v2(prices).dropna()
    adaptive_threshold_series = compute_adaptive_threshold(rotation_series_v2)
    _rs_std_v1    = float(rotation_series_v1.std()) if len(rotation_series_v1) > 5 else 5.0
    _threshold_v1 = round(_rs_std_v1 * 0.75, 2)
    _threshold_v2_now = (
        float(adaptive_threshold_series.iloc[-1])
        if not adaptive_threshold_series.empty else _threshold_v1
    )
    band_deriv_series, band_stato = compute_band_derivative(adaptive_threshold_series, window=10)

    # ── Regime label ──────────────────────────────────────────────────
    if rotation_score_adjusted > 1.5:
        regime  = "🟢 ROTATION: RISK ON"
        bg      = "#003300"
        comment = "Ciclici dominanti — volume confermato" if vol_mult == 1.0 else "Ciclici dominanti — volume parziale"
    elif rotation_score_adjusted < -1.5:
        regime  = "🔴 ROTATION: RISK OFF"
        bg      = "#330000"
        comment = "Difensivi dominanti su timeframe medio"
    else:
        regime  = "🟡 ROTATION: NEUTRAL"
        bg      = "#333300"
        comment = "Equilibrio ciclici/difensivi"

    if vol_conf >= 0.5:
        vol_conf_label = "✅ VOLUME CONFERMA"
        vol_conf_color = "#00ff55"
    elif vol_conf >= 0.0:
        vol_conf_label = "⚠️ VOLUME PARZIALE"
        vol_conf_color = "#ffaa00"
    else:
        vol_conf_label = "❌ VOLUME CONTRADDICE"
        vol_conf_color = "#ff4422"

    # ── Header: 4 box ────────────────────────────────────────────────
    col_box1, col_box2, col_box3, col_box4 = st.columns(4)

    with col_box1:
        st.markdown(f"""
        <div style="background:{bg};padding:16px 24px;border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;
                        text-transform:uppercase;margin-bottom:4px;">ROS Adjusted</div>
            <div style="font-size:1.5em;font-weight:bold;">{regime}</div>
            <div style="font-size:1.0em;margin-top:4px;color:#aaa;">{rotation_score_adjusted:.2f}</div>
            <div style="font-size:0.78em;color:#666;margin-top:4px;">{comment}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_box2:
        delta_v1_v2 = rotation_score_v2_scalar - rotation_score_v1
        delta_color = "#00ff55" if delta_v1_v2 >= 0 else "#ff4422"
        st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid #222;padding:16px 24px;
                    border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;
                        text-transform:uppercase;margin-bottom:6px;">Confronto v1 → v2 → adj</div>
            <div style="font-size:0.88em;color:#aaa;">
                v1 (33/33/33): <b style="color:#dddddd">{rotation_score_v1:.2f}</b>
            </div>
            <div style="font-size:0.88em;color:#aaa;margin-top:4px;">
                v2 (15/25/35/25): <b style="color:#dddddd">{rotation_score_v2_scalar:.2f}</b>
            </div>
            <div style="font-size:0.88em;color:#aaa;margin-top:4px;">
                adjusted (×{vol_mult}): <b style="color:#ff9900">{rotation_score_adjusted:.2f}</b>
            </div>
            <div style="font-size:0.80em;margin-top:6px;color:{delta_color};">
                Δ v1→v2: {delta_v1_v2:+.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_box3:
        st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid #222;padding:16px 24px;
                    border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;
                        text-transform:uppercase;margin-bottom:6px;">Vol Confirmation</div>
            <div style="font-size:1.1em;font-weight:bold;color:{vol_conf_color};margin-top:4px;">
                {vol_conf_label}
            </div>
            <div style="font-size:0.88em;color:#aaa;margin-top:6px;">
                Score: <b style="color:{vol_conf_color}">{vol_conf:+.2f}</b>
                &nbsp;·&nbsp; Mult: <b style="color:#ff9900">×{vol_mult}</b>
            </div>
            <div style="font-size:0.75em;color:#555;margin-top:6px;">
                Ciclici vol − Difensivi vol
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_box4:
        _bd_stato = band_stato["stato"] if "band_stato" in dir() else "N/D"
        _bd_color = band_stato["color"] if "band_stato" in dir() else "#888"
        _bd_deriv = band_stato["deriv"] if "band_stato" in dir() else float("nan")
        _bd_std   = band_stato.get("deriv_std", float("nan"))
        _bd_deriv_str = f"{_bd_deriv:+.2f}%" if not (isinstance(_bd_deriv, float) and _bd_deriv != _bd_deriv) else "N/D"
        st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid #222;padding:16px 24px;
                    border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;
                        text-transform:uppercase;margin-bottom:6px;">Banda — Velocità</div>
            <div style="font-size:1.0em;font-weight:bold;color:{band_stato['color']};margin-top:4px;">
                {band_stato['stato']}
            </div>
            <div style="font-size:0.85em;color:#aaa;margin-top:6px;">
                Δ banda 10gg: <b style="color:{band_stato['color']}">{band_stato['deriv']:+.2f}%</b>
            </div>
            <div style="font-size:0.72em;color:#555;margin-top:4px;">
                σ derivata: {band_stato['deriv_std']:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # ── Timeframe selector ────────────────────────────────────────────
    tf_rot = st.radio(
        "Storico grafico",
        ["1A", "2A", "3A", "5A", "Max"],
        index=0, horizontal=True,
        key="tf_rotation"
    )
    _tf_rot_days = {"1A": 365, "2A": 730, "3A": 1095, "5A": 1825, "Max": 99999}

    def slice_series(s, days):
        if s.empty:
            return s
        cutoff = s.index.max() - pd.Timedelta(days=days)
        return s[s.index >= cutoff]

    days_sel      = _tf_rot_days[tf_rot]
    plot_v1       = slice_series(rotation_series_v1, days_sel)
    plot_v2       = slice_series(rotation_series_v2, days_sel)
    plot_adaptive = slice_series(adaptive_threshold_series, days_sel)

    # ── Label confronto ───────────────────────────────────────────────
    st.markdown(
        '<div style="color:#555;font-size:0.78em;letter-spacing:0.06em;'
        'text-transform:uppercase;margin-bottom:6px;">'
        '◀ ROS v1 — pesi flat · soglia fissa &nbsp;|&nbsp; '
        'ROS v2 — pesi 15/25/35/25 · soglia adattiva · vol adjusted ▶'
        '</div>',
        unsafe_allow_html=True
    )

    col_g1, col_g2 = st.columns(2)

    # ── Grafico sinistro: ROS v1 ──────────────────────────────────────
    with col_g1:
        fig_v1 = go.Figure()
        fig_v1.add_trace(go.Scatter(
            x=plot_v1.index, y=plot_v1,
            mode="lines",
            line=dict(color="#888888", width=1.5),
            name="ROS v1",
            fill='tozeroy',
            fillcolor='rgba(100,100,100,0.12)'
        ))
        fig_v1.add_hline(
            y=_threshold_v1, line_dash="dot", line_color="#00AA00",
            annotation_text=f"Risk On +{_threshold_v1:.1f} (fissa)",
            annotation_position="right",
            annotation_font=dict(size=9, color="#00AA00")
        )
        fig_v1.add_hline(y=0.0, line_dash="solid", line_color="#444444")
        fig_v1.add_hline(
            y=-_threshold_v1, line_dash="dot", line_color="#AA0000",
            annotation_text=f"Risk Off -{_threshold_v1:.1f} (fissa)",
            annotation_position="right",
            annotation_font=dict(size=9, color="#AA0000")
        )
        fig_v1.update_layout(
            height=300,
            margin=dict(l=40, r=90, t=30, b=40),
            paper_bgcolor="#000000", plot_bgcolor="#000000",
            font_color="white", showlegend=False,
            title=dict(
                text="ROS v1 — originale",
                font=dict(size=10, color="#666"), x=0, xanchor="left"
            ),
            yaxis=dict(gridcolor="#1a1a1a", title=""),
            xaxis=dict(gridcolor="#1a1a1a")
        )
        st.plotly_chart(fig_v1, use_container_width=True)

    # ── Grafico destro: ROS v2 adjusted ──────────────────────────────
    with col_g2:
        fig_v2 = go.Figure()

        # Banda soglia adattiva
        if not plot_adaptive.empty and not plot_v2.empty:
            common_idx   = plot_v2.index.intersection(plot_adaptive.index)
            if len(common_idx) > 0:
                adap_aligned = plot_adaptive.reindex(common_idx).ffill()
                fig_v2.add_trace(go.Scatter(
                    x=common_idx, y=adap_aligned,
                    mode="lines",
                    line=dict(color="#00AA00", width=1, dash="dot"),
                    showlegend=False, opacity=0.55
                ))
                fig_v2.add_trace(go.Scatter(
                    x=common_idx, y=-adap_aligned,
                    mode="lines",
                    line=dict(color="#AA0000", width=1, dash="dot"),
                    fill='tonexty',
                    fillcolor='rgba(80,80,80,0.07)',
                    showlegend=False, opacity=0.55
                ))

        fig_v2.add_trace(go.Scatter(
            x=plot_v2.index, y=plot_v2,
            mode="lines",
            line=dict(color="#DDDDDD", width=2),
            name="ROS v2",
            fill='tozeroy',
            fillcolor='rgba(120,120,120,0.13)'
        ))

        # Diamante punto corrente adjusted
        if not plot_v2.empty:
            last_date = plot_v2.index[-1]
            last_val  = float(plot_v2.iloc[-1])
            adj_val   = last_val * vol_mult
            mk_color  = "#00ff55" if vol_mult == 1.0 else "#ffaa00" if vol_mult == 0.75 else "#ff4422"
            fig_v2.add_trace(go.Scatter(
                x=[last_date], y=[adj_val],
                mode="markers",
                marker=dict(size=12, color=mk_color, symbol="diamond",
                            line=dict(color="white", width=1.5)),
                name=f"adj ×{vol_mult}",
                hovertemplate=f"ROS adjusted: {adj_val:.2f}<extra></extra>"
            ))

        fig_v2.add_hline(y=0.0, line_dash="solid", line_color="#444444")

        # Annotazioni soglia adattiva corrente
        if not plot_v2.empty:
            fig_v2.add_annotation(
                x=plot_v2.index[-1], y=_threshold_v2_now,
                text=f"+{_threshold_v2_now:.1f} adattiva",
                showarrow=False, font=dict(size=9, color="#00AA00"),
                xanchor="right", yanchor="bottom"
            )
            fig_v2.add_annotation(
                x=plot_v2.index[-1], y=-_threshold_v2_now,
                text=f"-{_threshold_v2_now:.1f} adattiva",
                showarrow=False, font=dict(size=9, color="#AA0000"),
                xanchor="right", yanchor="top"
            )

        fig_v2.update_layout(
            height=300,
            margin=dict(l=40, r=90, t=30, b=40),
            paper_bgcolor="#000000", plot_bgcolor="#000000",
            font_color="white", showlegend=False,
            title=dict(
                text=f"ROS v2 — adjusted · ◆ = punto corrente ×{vol_mult}",
                font=dict(size=10, color="#666"), x=0, xanchor="left"
            ),
            yaxis=dict(gridcolor="#1a1a1a", title=""),
            xaxis=dict(gridcolor="#1a1a1a")
        )
        st.plotly_chart(fig_v2, use_container_width=True)

    # ── Int.4 — grafico derivata banda adattiva ──────────────────────
    if not band_deriv_series.empty:
        plot_deriv = slice_series(band_deriv_series, days_sel)
        if not plot_deriv.empty:
            import math as _m4
            _s_str = band_stato["soglia_stretta"]
            _s_lar = band_stato["soglia_larga"]
            _s_ok  = not _m4.isnan(_s_str)
            _l_ok  = not _m4.isnan(_s_lar)
            bar_colors_d = []
            for _v in plot_deriv:
                if _s_ok and _v < _s_str * 2:   bar_colors_d.append("#ff4422")
                elif _s_ok and _v < _s_str:      bar_colors_d.append("#ffaa00")
                elif _l_ok and _v > _s_lar * 2:  bar_colors_d.append("#44aaff")
                elif _v > 0:                      bar_colors_d.append("#555555")
                else:                             bar_colors_d.append("#333333")
            fig_d4 = go.Figure()
            fig_d4.add_trace(go.Bar(
                x=plot_deriv.index, y=plot_deriv,
                marker_color=bar_colors_d,
                hovertemplate="Delta banda: %{y:+.2f}%<extra></extra>",
            ))
            fig_d4.add_hline(y=0, line_color="#555", line_width=1)
            if _s_ok:
                fig_d4.add_hline(y=_s_str, line_dash="dot", line_color="#ffaa00",
                    annotation_text="stretta", annotation_font=dict(size=8, color="#ffaa00"),
                    annotation_position="right")
                fig_d4.add_hline(y=_s_str * 2, line_dash="dot", line_color="#ff4422",
                    annotation_text="stretta rapida", annotation_font=dict(size=8, color="#ff4422"),
                    annotation_position="right")
            if _l_ok:
                fig_d4.add_hline(y=_s_lar * 2, line_dash="dot", line_color="#44aaff",
                    annotation_text="larga rapida", annotation_font=dict(size=8, color="#44aaff"),
                    annotation_position="right")
            fig_d4.update_layout(
                height=155,
                margin=dict(l=40, r=110, t=22, b=30),
                paper_bgcolor="#000", plot_bgcolor="#000",
                font_color="white", showlegend=False,
                title=dict(
                    text="Int.4 — Velocita banda adattiva (10gg)  |  rosso=stringe [pericolo imminente] · grigio=stabile · blu=allarga [segnale ritarda]",
                    font=dict(size=9, color="#555"), x=0, xanchor="left"
                ),
                yaxis=dict(gridcolor="#1a1a1a", ticksuffix="%", title=""),
                xaxis=dict(gridcolor="#1a1a1a"),
            )
            st.plotly_chart(fig_d4, use_container_width=True)

    # ── Legenda interventi ────────────────────────────────────────────
    _bd_leg_str = f"{band_stato['stato']} ({band_stato['deriv']:+.2f}%)"
    st.markdown(f"""
    <div style="background:#080808;border:1px solid #1a1a1a;border-radius:8px;
                padding:12px 20px;margin-top:2px;font-size:0.80em;color:#666;
                display:flex;gap:28px;flex-wrap:wrap;">
        <span><b style="color:#ff9900">Int.1</b> — peso 1W=15% leading edge · pesi 15·25·35·25</span>
        <span><b style="color:#ff9900">Int.2</b> — soglia adattiva rolling(252)x0.75
              · ora: +/-{_threshold_v2_now:.2f} vs fissa +/-{_threshold_v1:.2f}</span>
        <span><b style="color:#ff9900">Int.3</b> — vol mult x{vol_mult}
              (score {vol_conf:+.2f}) · <span style="color:{vol_conf_color}">{vol_conf_label}</span></span>
        <span><b style="color:#ff9900">Int.4</b> — banda: <span style="color:{band_stato['color']}">{_bd_leg_str}</span></span>
    </div>
    """, unsafe_allow_html=True)

    # ── Expander: Vol Confirmation dettaglio ──────────────────────────
    with st.expander("🔬 Dettaglio Vol Confirmation per settore", expanded=False):
        vol_detail_rows = []
        for t in CYCLICALS + DEFENSIVES:
            plain = vol_plain.get(t, "[B~ M~] INDECISO")
            score = VOL_SCORE_MAP.get(plain, 0.0)
            vol_detail_rows.append({
                "Ticker":     t,
                "Tipo":       "Ciclico" if t in CYCLICALS else "Difensivo",
                "Vol Signal": plain,
                "Score":      score,
            })
        vd_df = pd.DataFrame(vol_detail_rows)

        def style_vol_score(val):
            if val > 0.5:  return "color:#00ff55;font-weight:bold"
            if val > 0:    return "color:#88cc88"
            if val < -0.5: return "color:#ff4422;font-weight:bold"
            if val < 0:    return "color:#cc6644"
            return "color:#666"

        def style_tipo(val):
            return "color:#ffaa00" if val == "Ciclico" else "color:#44aaff"

        st.dataframe(
            vd_df.style
                .map(style_vol_score, subset=["Score"])
                .map(style_tipo,      subset=["Tipo"]),
            use_container_width=True, hide_index=True,
        )

        cyc_avg = np.mean([VOL_SCORE_MAP.get(vol_plain.get(t, "[B~ M~] INDECISO"), 0.0) for t in CYCLICALS])
        def_avg = np.mean([VOL_SCORE_MAP.get(vol_plain.get(t, "[B~ M~] INDECISO"), 0.0) for t in DEFENSIVES])
        st.markdown(
            f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:6px;'
            f'padding:8px 16px;margin-top:6px;font-size:0.82em;color:#888;'
            f'display:flex;gap:28px;flex-wrap:wrap;">'
            f'<span>Media ciclici: <b style="color:#ffaa00">{cyc_avg:+.2f}</b></span>'
            f'<span>Media difensivi: <b style="color:#44aaff">{def_avg:+.2f}</b></span>'
            f'<span>Vol confirmation: <b style="color:{vol_conf_color}">{vol_conf:+.2f}</b></span>'
            f'<span>Multiplier: <b style="color:#ff9900">×{vol_mult}</b></span>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Expander: Episodi Risk Off (su serie v2 + soglia adattiva) ────
    with st.expander("🔬 Episodi Risk Off — analisi storica", expanded=False):
        confirm_sel = st.radio(
            "Giorni conferma anti-whipsaw",
            [2, 3, 5],
            index=1, horizontal=True,
            key="rs_confirm_days",
            help="Numero di giorni consecutivi sotto soglia necessari per confermare un episodio"
        )

        episodes = compute_risk_off_episodes(
            rotation_series_v2, _threshold_v2_now, confirm_days=confirm_sel
        )

        if not episodes:
            st.info("Nessun episodio Risk Off identificato con i parametri correnti.")
        else:
            st.markdown(
                f'<div style="color:#555;font-size:0.78em;margin-bottom:8px;">'
                f'Soglia adattiva corrente: RS &lt; <b style="color:#AA0000">-{_threshold_v2_now:.1f}</b> · '
                f'Conferma: <b>{confirm_sel}</b> giorni · '
                f'Episodi: <b style="color:#ff9900">{len(episodes)}</b>'
                f'</div>',
                unsafe_allow_html=True
            )

            rows_ep = []
            for i, ep in enumerate(episodes, 1):
                stato   = "🔴 APERTO" if ep["open"] else "✅ chiuso"
                end_str = "in corso"  if ep["open"] else ep["end"].strftime("%d/%m/%Y")
                rows_ep.append({
                    "#":           i,
                    "Inizio":      ep["start"].strftime("%d/%m/%Y"),
                    "Confermato":  ep["confirmed"].strftime("%d/%m/%Y"),
                    "Fine":        end_str,
                    "Durata (gg)": ep["duration"],
                    "RS minimo":   ep["rs_min"],
                    "Data minimo": ep["rs_min_date"].strftime("%d/%m/%Y"),
                    "Stato":       stato,
                })
            ep_df = pd.DataFrame(rows_ep)

            def style_ep(row):
                if "APERTO" in str(row["Stato"]):
                    return ["background-color:#1a0000; color:#ff4422"] * len(row)
                return ["color:#aaaaaa"] * len(row)

            def style_rs_min(val):
                try:
                    v = float(val)
                    if v < -7: return "color:#ff4422;font-weight:bold"
                    if v < -5: return "color:#ffaa00;font-weight:bold"
                    return "color:#888888"
                except Exception:
                    return ""

            st.dataframe(
                ep_df.style
                    .apply(style_ep, axis=1)
                    .map(style_rs_min, subset=["RS minimo"]),
                use_container_width=True, hide_index=True,
                column_config={
                    "Durata (gg)": st.column_config.NumberColumn("Durata (gg)", format="%d"),
                    "RS minimo":   st.column_config.NumberColumn("RS minimo",   format="%.2f"),
                }
            )

            closed = [e for e in episodes if not e["open"]]
            if closed:
                durate = [e["duration"] for e in closed]
                minimi = [e["rs_min"]   for e in closed]
                st.markdown(
                    f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;'
                    f'padding:10px 20px;margin-top:8px;font-size:0.82em;color:#888;'
                    f'display:flex;gap:28px;flex-wrap:wrap;">'
                    f'<span>Episodi chiusi: <b style="color:#ff9900">{len(closed)}</b></span>'
                    f'<span>Durata media: <b style="color:#ff9900">{int(sum(durate)/len(durate))} gg</b></span>'
                    f'<span>Durata max: <b style="color:#ff9900">{max(durate)} gg</b></span>'
                    f'<span>RS minimo storico: <b style="color:#ff4422">{min(minimi):.2f}</b></span>'
                    f'<span>RS minimo medio: <b style="color:#ffaa00">{sum(minimi)/len(minimi):.2f}</b></span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                # ── Cross-asset OBV Flow Chart ────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<h4 style="color:#ff9900;margin-bottom:2px;">📊 Cross-Asset OBV Flow</h4>'
        '<p style="color:#555;font-size:0.80em;margin-top:0;">'
        'flowEMA normalizzata su scala comune — confronto volumetrico cross-settoriale impossibile in TradingView</p>',
        unsafe_allow_html=True
    )

    col_obv1, col_obv2, col_obv3 = st.columns([3, 1, 1])
    with col_obv1:
        obv_tickers_sel = st.multiselect(
            "Strumenti da confrontare",
            options=SECTORS + [BENCHMARK],
            default=["XLK", "XLY", "XLF", "XLV", "SPY"],
            key="obv_cross_sel"
        )
    with col_obv2:
        obv_tf = st.radio(
            "Finestra chart",
            ["6M", "1A", "2A", "Max"],
            index=1, horizontal=False,
            key="obv_tf_sel"
        )
    with col_obv3:
        show_trend_filter = st.checkbox(
            "Mostra Trend Filter",
            value=False,
            key="obv_show_trend"
        )

    _obv_tf_days = {"6M": 126, "1A": 252, "2A": 504, "Max": 99999}

    if obv_tickers_sel:
        obv_palette = [
            "#ff9900", "#00ff55", "#44aaff", "#ff4422", "#ffff44",
            "#bb44ff", "#00ffcc", "#ff66cc", "#88cc88", "#cc8844",
            "#4488ff", "#ff8844"
        ]

        fig_obv = go.Figure()
        obv_loaded = 0

        for i, ticker in enumerate(obv_tickers_sel):
            try:
                if isinstance(ohlcv_long.columns, pd.MultiIndex):
                    cl = ohlcv_long["Close"][ticker].dropna()
                    vo = ohlcv_long["Volume"][ticker].dropna()
                else:
                    cl = ohlcv_long["Close"].dropna()
                    vo = ohlcv_long["Volume"].dropna()

                if cl.empty or vo.empty or len(cl) < 60:
                    continue

                result = compute_obv_flow(cl, vo)
                fe = result["flow_ema"].dropna()
                ft = result["flow_trend"].dropna()

                if fe.empty:
                    continue

                # Slice per timeframe selezionato
                days_obv = _obv_tf_days[obv_tf]
                if days_obv < 99999:
                    cutoff = fe.index.max() - pd.Timedelta(days=days_obv)
                    fe = fe[fe.index >= cutoff]
                    ft = ft[ft.index >= cutoff]

                color = obv_palette[i % len(obv_palette)]

                # Normalizzazione z-score per confronto visivo su scala comune
                fe_mean = fe.mean()
                fe_std  = fe.std()
                if fe_std == 0 or np.isnan(fe_std):
                    continue
                fe_norm = (fe - fe_mean) / fe_std
                ft_norm = (ft - fe_mean) / fe_std  # stessa scala

                fig_obv.add_trace(go.Scatter(
                    x=fe_norm.index,
                    y=fe_norm,
                    mode="lines",
                    name=ticker,
                    line=dict(color=color, width=2),
                    hovertemplate=f"<b>{ticker}</b><br>%{{x|%d %b %Y}}<br>Flow (z): %{{y:.2f}}<extra></extra>"
                ))

                if show_trend_filter and not ft_norm.empty:
                    fig_obv.add_trace(go.Scatter(
                        x=ft_norm.index,
                        y=ft_norm,
                        mode="lines",
                        name=f"{ticker} trend",
                        line=dict(color=color, width=1, dash="dot"),
                        opacity=0.45,
                        showlegend=False,
                        hovertemplate=f"<b>{ticker} trend</b><br>%{{x|%d %b %Y}}<br>%{{y:.2f}}<extra></extra>"
                    ))

                obv_loaded += 1

            except Exception:
                continue

        if obv_loaded == 0:
            st.warning("Dati OBV non disponibili per i ticker selezionati.")
        else:
            fig_obv.add_hline(
                y=0, line_color="#444", line_width=1,
                line_dash="dot"
            )
            fig_obv.update_layout(
                height=380,
                paper_bgcolor="#000000",
                plot_bgcolor="#000000",
                font=dict(color="white", size=10),
                title=dict(
                    text="OBV Flow EMA — normalizzata z-score (scala comune)  |  sopra 0 = accumulo strutturale relativo",
                    font=dict(size=9, color="#555"),
                    x=0, xanchor="left"
                ),
                xaxis=dict(gridcolor="#1a1a1a"),
                yaxis=dict(
                    gridcolor="#1a1a1a",
                    title="Flow z-score",
                    zeroline=False
                ),
                legend=dict(
                    font=dict(size=9),
                    bgcolor="rgba(0,0,0,0.6)",
                    bordercolor="#333",
                    borderwidth=1,
                    orientation="h",
                    y=1.04, x=0, xanchor="left"
                ),
                margin=dict(l=50, r=30, t=45, b=40),
                hovermode="x unified"
            )
            st.plotly_chart(fig_obv, use_container_width=True)

            # Tabella regime corrente per i ticker selezionati
            regime_rows = []
            for ticker in obv_tickers_sel:
                r = obv_regime.get(ticker, "N/D")
                regime_rows.append({
                    "Ticker":      ticker,
                    "Flow Regime": r,
                    "RSR 1M":      round(float(rsr_df.loc[ticker, "1M"]), 2) if ticker in rsr_df.index else np.nan,
                    "Vol Signal":  vol_plain.get(ticker, "—"),
                })
            reg_df = pd.DataFrame(regime_rows)

            def _style_regime(val):
                if val == "BULL FLOW": return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
                if val == "BEAR FLOW": return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
                return "color:#888"

            def _style_vol_plain(val):
                v = str(val)
                if "ACCUMULO"   in v: return "color:#00ff55;font-weight:bold"
                if "DISTRIBUZ"  in v: return "color:#ff4422;font-weight:bold"
                if "ESAURIM"    in v: return "color:#ffaa00;font-weight:bold"
                if "INVERSIONE" in v: return "color:#44aaff;font-weight:bold"
                return "color:#888"

            st.dataframe(
                reg_df.style
                    .map(_style_regime,    subset=["Flow Regime"])
                    .map(_style_vol_plain, subset=["Vol Signal"]),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Flow Regime": st.column_config.TextColumn("Flow Regime", width="small"),
                    "Vol Signal":  st.column_config.TextColumn("Vol Signal",  width="medium"),
                    "RSR 1M":      st.column_config.NumberColumn("RSR 1M",    format="%.2f"),
                }
            )

    st.markdown(
        '<div style="background:#080808;border:1px solid #1a1a1a;border-radius:6px;'
        'padding:8px 16px;margin-top:6px;font-size:0.78em;color:#555;">'
        '<b style="color:#ff9900">Flow Regime</b>: flowEMA &gt; flowTrend → BULL · '
        'flowEMA &lt; flowTrend → BEAR &nbsp;|&nbsp; '
        '<b style="color:#ff9900">Scala</b>: z-score per confronto cross-asset '
        '(parametri Daily: vol=20 · ema=13 · trend=50)'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Spiegazione ───────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#0d0d0d;padding:25px;border-radius:10px;
                font-size:1.0em;line-height:1.7;margin-top:8px;">
    <h3 style="color:#ff9900;margin-top:0;">📊 ROS 2.0 — Tre Interventi</h3>

    <b style="color:#ff9900">Intervento 1 — Leading Edge 1W</b><br>
    Aggiunto timeframe settimanale (peso 15%) per catturare rotazioni emergenti prima
    che si consolidino nel mensile. Pesi: 1W=15% · 1M=25% · 3M=35% · 6M=25%.<br><br>

    <b style="color:#ff9900">Intervento 2 — Soglia Adattiva</b><br>
    Soglia calcolata su rolling std 252gg × 0.75. In mercati laterali si restringe
    (meno falsi segnali), in mercati direzionali si allarga (segnali più significativi).
    Corrente: <b style="color:#ff9900">±{_threshold_v2_now:.2f}</b>
    vs fissa v1: <b style="color:#888">±{_threshold_v1:.2f}</b><br><br>

    <b style="color:#ff9900">Intervento 3 — Vol Confirmation</b><br>
    Aggrega i VWDS settoriali in un Vol Confirmation Score ({vol_conf:+.2f}).
    Quando il volume contraddice il momentum relativo, il segnale viene scalato:
    ×1.0 (confermato) · ×0.75 (parziale) · ×0.5 (contradditorio).<br>
    Stato corrente: <b style="color:{vol_conf_color}">{vol_conf_label}</b> → ×{vol_mult}

    <h3 style="color:#ff9900;margin-top:20px;">🎯 Situazione Attuale</h3>
    <div style="background:#1a1a1a;padding:15px;border-radius:8px;">
        ROS v1: <b>{rotation_score_v1:.2f}</b> →
        ROS v2: <b>{rotation_score_v2_scalar:.2f}</b> →
        ROS adjusted: <b style="color:#ff9900">{rotation_score_adjusted:.2f}</b>
        · {comment}
    </div>
    </div>
    """, unsafe_allow_html=True)


# ========================
# TAB 5 — BUBBLE CHART S&P 500
# ========================
with tab5:
    tf_options = {
        "1W":  5, "1M": 21, "3M": 63, "6M": 126,
        "YTD": (datetime.today() - datetime(datetime.today().year, 1, 1)).days
    }
    tf_sel  = st.radio("Timeframe", options=list(tf_options.keys()), index=1, horizontal=True)
    tf_days = tf_options[tf_sel]

    with st.spinner(f"Caricamento dati S&P 500 ({tf_sel})… prima volta ~30s, poi in cache"):
        sp500_df = load_sp500_data(tf_days)

    if sp500_df.empty:
        st.error("Impossibile caricare i dati S&P 500. Riprova tra qualche minuto.")
    else:
        sector_stats = (
            sp500_df.groupby("Sector")
            .apply(lambda g: pd.Series({
                "Totale":   len(g),
                "Positive": (g["Return"] > 0).sum(),
                "Negative": (g["Return"] <= 0).sum(),
                "Pct_pos":  round((g["Return"] > 0).mean() * 100, 1),
                "Avg_ret":  round(g["Return"].mean(), 2),
            }), include_groups=False)
            .reset_index()
            .sort_values("Pct_pos", ascending=False)
        )

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="% Positive", x=sector_stats["Sector"], y=sector_stats["Pct_pos"],
            marker_color="#00cc44",
            text=sector_stats["Pct_pos"].astype(str) + "%",
            textposition="outside", textfont=dict(size=10, color="#00cc44"),
        ))
        fig_bar.add_hline(y=50, line_dash="dot", line_color="#555555",
                          annotation_text="50%", annotation_font_color="#888", annotation_position="right")
        fig_bar.update_layout(
            height=220, paper_bgcolor="#000", plot_bgcolor="#000",
            font=dict(color="white", size=11),
            title=dict(text=f"% Titoli Positivi per Settore — {tf_sel}", font=dict(size=13, color="#ff9900")),
            xaxis=dict(tickangle=-30, gridcolor="#111"),
            yaxis=dict(range=[0, 115], gridcolor="#111", ticksuffix="%"),
            margin=dict(l=40, r=20, t=45, b=80), showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        tot = len(sp500_df)
        pos = (sp500_df["Return"] > 0).sum()
        pct = round(pos / tot * 100, 1)
        colore = "#00ff55" if pct >= 50 else "#ff4422"
        st.markdown(
            f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;'
            f'padding:10px 20px;margin-bottom:10px;font-size:1.05em;">'
            f'📊 Su timeframe <b>{tf_sel}</b>: '
            f'<b style="color:{colore}">{pos} titoli su {tot} ({pct}%)</b> '
            f'sono in territorio positivo nell\'S&P 500</div>',
            unsafe_allow_html=True
        )

        sector_order = sector_stats["Sector"].tolist()
        sp500_df["SectorRank"] = sp500_df["Sector"].map({s: i for i, s in enumerate(sector_order)})
        sp500_df = sp500_df.sort_values("SectorRank")
        colors_b = sp500_df["Return"].apply(lambda r: "#00cc44" if r > 0 else "#ff3322")

        np.random.seed(42)
        jitter = np.random.uniform(-0.35, 0.35, size=len(sp500_df))
        x_vals = sp500_df["SectorRank"] + jitter

        fig_bubble = go.Figure()
        fig_bubble.add_hline(y=0, line_color="#444444", line_width=1.5)
        fig_bubble.add_trace(go.Scatter(
            x=x_vals, y=sp500_df["Return"], mode="markers",
            marker=dict(size=5, color=colors_b, opacity=0.75, line=dict(width=0)),
            text=sp500_df["Ticker"] + "<br>" + sp500_df["Return"].astype(str) + "%",
            hovertemplate="%{text}<extra></extra>", showlegend=False,
        ))

        tick_labels = []
        for _, row in sector_stats.iterrows():
            short = row["Sector"].replace(" & ", "/").replace(" ", "<br>")
            tick_labels.append(
                f"{short}<br>"
                f"<span style='color:#00cc44'>{int(row['Positive'])}↑</span> "
                f"<span style='color:#ff3322'>{int(row['Negative'])}↓</span>"
            )

        fig_bubble.update_layout(
            height=520, paper_bgcolor="#000000", plot_bgcolor="#000000",
            font=dict(color="white", size=10),
            title=dict(text=f"S&P 500 — Ritorno {tf_sel} per Titolo e Settore", font=dict(size=14, color="#ff9900")),
            xaxis=dict(tickmode="array", tickvals=list(range(len(sector_order))),
                       ticktext=tick_labels, tickangle=0, gridcolor="#111111", showline=False),
            yaxis=dict(title="Ritorno %", gridcolor="#1a1a1a", zeroline=False, ticksuffix="%"),
            margin=dict(l=60, r=20, t=50, b=120),
            hoverlabel=dict(bgcolor="#111", font_size=12),
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

        with st.expander("📋 Tabella dettaglio settori", expanded=False):
            display_stats = sector_stats[["Sector","Totale","Positive","Negative","Pct_pos","Avg_ret"]].copy()
            display_stats.columns = ["Settore","Totale","Positive ↑","Negative ↓","% Positive","Ritorno Medio %"]
            def style_pct(val):
                if val >= 60: return "color:#00ff55; font-weight:bold"
                if val <= 40: return "color:#ff4422; font-weight:bold"
                return "color:#ffff44"
            st.dataframe(
                display_stats.style.map(style_pct, subset=["% Positive"]),
                use_container_width=True, hide_index=True
            )


# ========================
# TAB 6 — P/E
# ========================
with tab6:
    st.markdown(
        '<h3 style="color:#ff9900;margin-bottom:4px;">📐 Valutazione P/E — Attuale vs Storia</h3>'
        '<p style="color:#666;font-size:0.85em;margin-top:0;">P/E live da worldperatio.com · Medie storiche da worldperatio.com · stessa metodologia</p>'
        '<p style="color:#444;font-size:0.78em;margin-top:4px;">📅 Dati storici aggiornati a: <b style="color:#ff9900">Febbraio 2026</b></p>',
        unsafe_allow_html=True
    )

    period_sel = st.radio(
        "Confronta con media storica",
        options=["Last 1Y","Last 3Y","Last 5Y","Last 10Y","Last 20Y"],
        index=2, horizontal=True
    )

    pe_hist = load_pe_historical()

    if pe_hist is None:
        st.warning("⚠️ File pe_historical.xlsx non trovato. Le altre tab funzionano normalmente.")
    else:
        with st.spinner("Scarico P/E live da worldperatio.com..."):
            pe_live, _pe_fallback = load_pe_live_worldperatio(SECTORS)

        if _pe_fallback:
            st.markdown(
                f'<div style="background:#1a1000;border:1px solid #332200;border-radius:6px;'
                f'padding:6px 14px;margin-bottom:8px;font-size:0.78em;color:#aa7700;">'
                f'⚠️ worldperatio non raggiungibile per: <b>{", ".join(_pe_fallback)}</b> — '
                f'usato fallback yfinance (fonte eterogenea, interpretare con cautela)</div>',
                unsafe_allow_html=True
            )

        etf_sectors = {
            "XLK":"Info Technology","XLY":"Cons Discretionary","XLF":"Financials",
            "XLC":"Comm Services","XLV":"Health Care","XLP":"Cons Staples",
            "XLI":"Industrials","XLE":"Energy","XLB":"Materials","XLU":"Utilities","XLRE":"Real Estate",
        }

        rows = []
        for etf, sector_name in etf_sectors.items():
            pe_now  = pe_live.get(etf)
            avg_col = f"{etf}_AvgPE"
            std_col = f"{etf}_StdDev"

            if period_sel not in pe_hist.index:
                continue

            avg_pe  = pe_hist.loc[period_sel, avg_col] if avg_col in pe_hist.columns else None
            std_dev = pe_hist.loc[period_sel, std_col] if std_col in pe_hist.columns else None

            if pe_now and avg_pe and std_dev and std_dev > 0:
                dev_live = round((pe_now - avg_pe) / std_dev, 2)
            else:
                dev_live = None

            def valuation_label(dev):
                if dev is None:      return "N/D",       "#888888"
                if dev < 0:          return "Cheap",     "#00ff55"
                if dev < 0.5:        return "Fair",      "#aaaaaa"
                if dev < 1.5:        return "Moderato",  "#ffff44"
                if dev < 2.5:        return "Overvalued","#ffaa00"
                return "Expensive",  "#ff4422"

            label, color = valuation_label(dev_live)
            rows.append({
                "ETF": etf, "Settore": sector_name,
                "P/E Live": pe_now, f"Avg P/E ({period_sel})": avg_pe,
                "Std Dev": std_dev, "Dev σ (live)": dev_live,
                "Valutazione": label, "_color": color,
            })

        comp_df = pd.DataFrame(rows)

        bar_colors_pe = []
        for _, r in comp_df.iterrows():
            d = r["Dev σ (live)"]
            if d is None:     bar_colors_pe.append("#555555")
            elif d < 0:       bar_colors_pe.append("#00ff55")
            elif d < 0.5:     bar_colors_pe.append("#aaaaaa")
            elif d < 1.5:     bar_colors_pe.append("#ffff44")
            elif d < 2.5:     bar_colors_pe.append("#ffaa00")
            else:             bar_colors_pe.append("#ff4422")

        fig_pe = go.Figure()
        fig_pe.add_trace(go.Bar(
            x=comp_df["ETF"], y=comp_df["Dev σ (live)"],
            marker_color=bar_colors_pe,
            text=[f"{v:.2f}σ" if v is not None else "N/D" for v in comp_df["Dev σ (live)"]],
            textposition="outside", textfont=dict(size=11, color="white"),
            hovertemplate="<b>%{x}</b><br>Deviazione: %{y:.2f}σ<extra></extra>",
        ))
        fig_pe.add_hline(y=0,    line_color="#444444", line_width=1)
        fig_pe.add_hline(y=1.5,  line_dash="dot", line_color="#ffaa00",
                         annotation_text="Overvalued", annotation_font_color="#ffaa00", annotation_position="right")
        fig_pe.add_hline(y=2.5,  line_dash="dot", line_color="#ff4422",
                         annotation_text="Expensive",  annotation_font_color="#ff4422", annotation_position="right")
        fig_pe.add_hline(y=-0.5, line_dash="dot", line_color="#00ff55",
                         annotation_text="Cheap",      annotation_font_color="#00ff55", annotation_position="right")
        fig_pe.update_layout(
            height=320, paper_bgcolor="#000000", plot_bgcolor="#000000",
            font=dict(color="white", size=11),
            title=dict(text=f"Deviazione P/E Live vs Media {period_sel}  (σ)", font=dict(size=13, color="#ff9900")),
            xaxis=dict(gridcolor="#111"), yaxis=dict(gridcolor="#1a1a1a", ticksuffix="σ"),
            margin=dict(l=40, r=80, t=50, b=40), showlegend=False,
        )
        st.plotly_chart(fig_pe, use_container_width=True)

        display_cols = ["ETF","Settore","P/E Live",f"Avg P/E ({period_sel})","Std Dev","Dev σ (live)","Valutazione"]
        display_df   = comp_df[display_cols].copy()

        def style_valuation(val):
            colors_map = {
                "Cheap":"color:#00ff55;font-weight:bold","Fair":"color:#aaaaaa",
                "Moderato":"color:#ffff44;font-weight:bold","Overvalued":"color:#ffaa00;font-weight:bold",
                "Expensive":"color:#ff4422;font-weight:bold","N/D":"color:#555555",
            }
            return colors_map.get(str(val), "")

        def style_dev(val):
            try:
                v = float(val)
                if v < 0:   return "color:#00ff55"
                if v < 0.5: return "color:#aaaaaa"
                if v < 1.5: return "color:#ffff44"
                if v < 2.5: return "color:#ffaa00"
                return "color:#ff4422"
            except Exception:
                return ""

        st.dataframe(
            display_df.style
                .map(style_valuation, subset=["Valutazione"])
                .map(style_dev, subset=["Dev σ (live)"])
                .format({
                    "P/E Live":                    lambda x: f"{x:.2f}" if x else "N/D",
                    f"Avg P/E ({period_sel})":     lambda x: f"{x:.2f}" if x else "N/D",
                    "Std Dev":                     lambda x: f"{x:.2f}" if x else "N/D",
                    "Dev σ (live)":                lambda x: f"{x:.2f}σ" if x else "N/D",
                }),
            use_container_width=True, hide_index=True,
        )

        st.markdown("""
        <div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;
                    padding:10px 20px;margin-top:8px;font-size:0.82em;color:#888;
                    display:flex;gap:20px;flex-wrap:wrap;">
            <span><b style="color:#00ff55">Cheap</b> — sotto la media storica</span>
            <span><b style="color:#aaaaaa">Fair</b> — entro 0.5σ dalla media</span>
            <span><b style="color:#ffff44">Moderato</b> — tra 0.5σ e 1.5σ</span>
            <span><b style="color:#ffaa00">Overvalued</b> — tra 1.5σ e 2.5σ</span>
            <span><b style="color:#ff4422">Expensive</b> — oltre 2.5σ dalla media</span>
        </div>
        """, unsafe_allow_html=True)


# ========================
# TAB 7 — TEMATICI
# ========================
with tab7:

    st.markdown(
        '<h3 style="color:#ff9900;margin-bottom:2px;">📌 ETF Tematici</h3>'
        '<p style="color:#555;font-size:0.82em;margin-top:0;">'
        'Performance assoluta · Delta vs benchmark di gruppo · Coerenza intra-settoriale · Scatter quadranti</p>',
        unsafe_allow_html=True,
    )

    with st.spinner("Caricamento prezzi tematici…"):
        th_prices = load_thematic_prices()

    if th_prices.empty:
        st.error("Impossibile scaricare i dati. Controlla la connessione.")
        st.stop()

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        tf_label = st.selectbox(
            "Timeframe analisi",
            ["1D","1W","1M","3M","6M","YTD","1A","2A"],
            index=4,
            key="tem_tf_main"
        )
    with c2:
        sector_opts = ["TUTTI"] + [s for s, _, _ in TEMATICI_STRUCT]
        sel_sector  = st.selectbox("Filtra gruppo", sector_opts, key="tem_sector")
    with c3:
        show_bm = st.checkbox("Mostra benchmark", value=True, key="tem_bm")

    tf_days_main = TF_DAYS[tf_label]

    rows_tem = []
    for sector, tickers, bm_ticker in TEMATICI_STRUCT:
        bm_ret = None
        if bm_ticker in th_prices.columns:
            bm_ret = safe_ret(th_prices[bm_ticker], tf_days_main)

        for ticker in tickers:
            if ticker not in th_prices.columns:
                continue
            s = th_prices[ticker].dropna()
            if len(s) < 3:
                continue

            abs_ret = safe_ret(s, tf_days_main)
            delta_bm = (abs_ret - bm_ret) if (abs_ret is not None and bm_ret is not None
                                               and not np.isnan(abs_ret) and not np.isnan(bm_ret)) else np.nan

            row = {
                "Gruppo":   sector,
                "Ticker":   ticker,
                "Tema":     TEMATICI_DESCRIPTIONS.get(ticker, ticker),
                "BM":       bm_ticker,
                "BM ret":   round(bm_ret, 2) if bm_ret and not np.isnan(bm_ret) else np.nan,
                "1D":       round(safe_ret(s, 1),   2),
                "1W":       round(safe_ret(s, 5),   2),
                "1M":       round(safe_ret(s, 21),  2),
                "3M":       round(safe_ret(s, 63),  2),
                "6M":       round(safe_ret(s, 126), 2),
                "YTD":      round(safe_ret(s, None),2),
                "1A":       round(safe_ret(s, 252), 2),
                "2A":       round(safe_ret(s, 504), 2),
                "vs BM":    round(delta_bm, 2) if not np.isnan(delta_bm) else np.nan,
            }
            rows_tem.append(row)

    tem_df = pd.DataFrame(rows_tem)

    if tem_df.empty:
        st.warning("Nessun dato disponibile per i ticker tematici.")
        st.stop()

    st.markdown("---")
    st.markdown(f"### 1 · Coerenza intra-gruppo — {tf_label}")

    valid_ret  = tem_df[tf_label].dropna()
    total_etf  = len(valid_ret)
    total_all  = len(tem_df)
    missing_n  = total_all - total_etf
    missing_tickers = tem_df[tem_df[tf_label].isna()]["Ticker"].tolist()

    pos_count = (valid_ret > 0).sum()
    pos_pct   = round(pos_count / total_etf * 100, 1) if total_etf > 0 else 0
    top_row   = tem_df.dropna(subset=[tf_label]).nlargest(1, tf_label).iloc[0] if total_etf > 0 else None
    bot_row   = tem_df.dropna(subset=[tf_label]).nsmallest(1, tf_label).iloc[0] if total_etf > 0 else None

    k1, k2, k3, k4 = st.columns(4)
    kpi_data = [
        (k1, "ETF con dati",        str(total_etf),                                           "#ff9900"),
        (k2, f"Positivi {tf_label}", f"{pos_count}/{total_etf} ({pos_pct}%)",
         "#00ff55" if pos_pct >= 50 else "#ff4422"),
        (k3, f"Top {tf_label}",
         f"{top_row['Ticker']} ({top_row[tf_label]:+.1f}%)" if top_row is not None else "—",  "#00ff55"),
        (k4, f"Worst {tf_label}",
         f"{bot_row['Ticker']} ({bot_row[tf_label]:+.1f}%)" if bot_row is not None else "—",  "#ff4422"),
    ]
    for col, label, val, color in kpi_data:
        col.markdown(
            f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;'
            f'padding:10px 14px;margin-bottom:6px;">'
            f'<div style="color:#555;font-size:0.75em;letter-spacing:0.06em">{label}</div>'
            f'<div style="color:{color};font-size:1.15em;font-weight:bold">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if missing_n > 0:
        st.markdown(
            f'<div style="background:#1a1000;border:1px solid #332200;border-radius:6px;'
            f'padding:6px 14px;margin-bottom:8px;font-size:0.78em;color:#aa7700;">'
            f'⚠️ <b>{missing_n} ETF esclusi</b> per storico insufficiente su <b>{tf_label}</b>: '
            f'{", ".join(missing_tickers)}</div>',
            unsafe_allow_html=True,
        )

    coerenza_data = []
    for sector, tickers, bm_ticker in TEMATICI_STRUCT:
        grp = tem_df[tem_df["Gruppo"] == sector][tf_label].dropna()
        if len(grp) == 0:
            continue
        n_pos  = int((grp > 0).sum())
        n_tot  = int(len(grp))
        pct    = round(n_pos / n_tot * 100, 1)
        bm_r   = tem_df[tem_df["Gruppo"] == sector]["BM ret"].dropna()
        bm_val = float(bm_r.iloc[0]) if len(bm_r) > 0 else np.nan
        coerenza_data.append({
            "Gruppo": sector, "Pct_pos": pct,
            "n_pos": n_pos, "n_tot": n_tot, "BM_ret": bm_val,
        })

    cdf_plot = pd.DataFrame(coerenza_data)

    col_chart, col_panel = st.columns([3, 2])

    with col_chart:
        bar_bm_colors = [
            "#00cc44" if (not np.isnan(r["BM_ret"]) and r["BM_ret"] >= 0) else "#cc2200"
            for _, r in cdf_plot.iterrows()
        ]

        bm_vals  = cdf_plot["BM_ret"].dropna()
        y_max_bm = bm_vals.max() if len(bm_vals) > 0 else 10
        y_min_bm = bm_vals.min() if len(bm_vals) > 0 else -5
        y_abs    = max(abs(y_max_bm), abs(y_min_bm))
        y_pad    = y_abs * 0.30
        y_top    = y_max_bm + y_pad + 5
        y_bot    = min(y_min_bm - y_pad, -3)

        fig_coh = go.Figure()

        for _, r in cdf_plot.iterrows():
            if np.isnan(r["BM_ret"]):
                continue
            fig_coh.add_shape(
                type="line",
                x0=r["Gruppo"], x1=r["Gruppo"],
                y0=0, y1=r["BM_ret"],
                line=dict(
                    color="#00cc44" if r["BM_ret"] >= 0 else "#cc2200",
                    width=8, dash="solid"
                ),
                opacity=0.45,
            )

        fig_coh.add_trace(go.Bar(
            x=cdf_plot["Gruppo"],
            y=cdf_plot["BM_ret"].fillna(0),
            marker=dict(color=bar_bm_colors, opacity=0.70,
                        line=dict(color="#333", width=1)),
            width=0.40,
            text=[f"{v:+.1f}%" if not np.isnan(v) else "n/d"
                  for v in cdf_plot["BM_ret"]],
            textposition="outside",
            textfont=dict(color="#888888", size=8),
            name=f"BM {tf_label}",
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"Benchmark {tf_label}: %{{y:+.1f}}%"
                "<extra></extra>"
            ),
        ))

        if show_bm:
            breadth_col = [
                "#00ff55" if r["Pct_pos"] >= 60
                else "#ffff44" if r["Pct_pos"] >= 40
                else "#ff4422"
                for _, r in cdf_plot.iterrows()
            ]
            hover_diamond = [
                f"<b>{r['Gruppo']}</b><br>"
                f"BM {tf_label}: {r['BM_ret']:+.1f}%<br>"
                f"Breadth: {r['Pct_pos']:.0f}% ({r['n_pos']}/{r['n_tot']})"
                for _, r in cdf_plot.iterrows()
            ]
            fig_coh.add_trace(go.Scatter(
                x=cdf_plot["Gruppo"],
                y=cdf_plot["BM_ret"].fillna(0),
                mode="markers",
                marker=dict(
                    symbol="diamond",
                    size=8,
                    color=breadth_col,
                    line=dict(color="#ffffff", width=1.2)
                ),
                name="Breadth ◆",
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover_diamond,
            ))

        fig_coh.add_hline(y=0, line_color="#555", line_width=1.5)
        fig_coh.update_layout(
            height=500,
            paper_bgcolor="#000",
            plot_bgcolor="#000",
            font=dict(color="white", size=9),
            title=dict(
                text=f"Ritorno benchmark {tf_label}  |  ◆ = breadth tematici (verde ≥60% · giallo 40-60% · rosso <40%)" if show_bm else f"Ritorno benchmark {tf_label}",
                font=dict(size=9, color="#555"),
                x=0, xanchor="left",
            ),
            xaxis=dict(tickangle=-25, gridcolor="#0a0a0a", tickfont=dict(size=8)),
            yaxis=dict(range=[y_bot, y_top], gridcolor="#111",
                       ticksuffix="%", zeroline=False,
                       tickfont=dict(size=8), title=None),
            legend=dict(font=dict(size=8), bgcolor="rgba(0,0,0,0)",
                        orientation="h", y=1.02, x=1, xanchor="right"),
            margin=dict(l=45, r=40, t=30, b=60),
            barmode="overlay",
        )
        st.plotly_chart(fig_coh, use_container_width=True)

    with col_panel:

        n_bm_pos       = (cdf_plot["BM_ret"] > 0).sum()
        n_bm_tot       = cdf_plot["BM_ret"].dropna().__len__()
        global_breadth = round(pos_pct, 1)
        avg_bm_ret     = round(cdf_plot["BM_ret"].mean(), 1)

        if n_bm_pos >= 9:
            regime_txt   = "RISK ON DIFFUSO"
            regime_color = "#00ff55"
            regime_icon  = "🟢"
        elif n_bm_pos >= 6:
            regime_txt   = "MOMENTUM MISTO"
            regime_color = "#ffff44"
            regime_icon  = "🟡"
        elif n_bm_pos >= 3:
            regime_txt   = "RISK OFF PARZIALE"
            regime_color = "#ffaa00"
            regime_icon  = "🟠"
        else:
            regime_txt   = "RISK OFF DIFFUSO"
            regime_color = "#ff4422"
            regime_icon  = "🔴"

        sorted_cdf  = cdf_plot.dropna(subset=["BM_ret"]).sort_values("BM_ret", ascending=False)
        bm_positivi = sorted_cdf[sorted_cdf["BM_ret"] >  0]
        bm_negativi = sorted_cdf[sorted_cdf["BM_ret"] <= 0].sort_values("BM_ret")

        all_positive = len(bm_negativi) == 0
        all_negative = len(bm_positivi) == 0

        if not all_negative:
            leader_df    = bm_positivi.head(3)
            leader_title = "▲ Leader benchmark"
            leader_note  = ""
        else:
            leader_df    = sorted_cdf.head(3)
            leader_title = "▲ Meno peggio"
            leader_note  = f'<div style="color:#555;font-style:italic;font-size:0.75em;margin-top:2px;">tutti i benchmark negativi su {tf_label}</div>'

        if not all_positive:
            corr_df    = bm_negativi.head(3)
            corr_title = "▼ Benchmark in correzione"
            corr_note  = ""
        else:
            corr_df    = sorted_cdf.tail(3).sort_values("BM_ret")
            corr_title = "▼ Gruppi meno forti"
            corr_note  = f'<div style="color:#555;font-style:italic;font-size:0.75em;margin-top:2px;">tutti i benchmark positivi su {tf_label}</div>'

        divergenze = []
        for _, r in cdf_plot.iterrows():
            if np.isnan(r["BM_ret"]):
                continue
            bm_pos   = r["BM_ret"] > 0
            brd_high = r["Pct_pos"] >= 60
            brd_low  = r["Pct_pos"] < 40
            if bm_pos and brd_low:
                divergenze.append(
                    f'<span style="color:#ffaa00">⚡ <b>{r["Gruppo"]}</b></span>: '
                    f'BM {r["BM_ret"]:+.1f}% ma breadth {r["Pct_pos"]:.0f}% '
                    f'→ <i>rally non confermato dai tematici</i>'
                )
            elif not bm_pos and brd_high:
                divergenze.append(
                    f'<span style="color:#44aaff">⚡ <b>{r["Gruppo"]}</b></span>: '
                    f'BM {r["BM_ret"]:+.1f}% ma breadth {r["Pct_pos"]:.0f}% '
                    f'→ <i>tematici reggono nonostante il benchmark</i>'
                )

        leader_html = "".join([
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:3px 0;border-bottom:1px solid #1a1a1a;">'
            f'<span style="color:#aaa;font-size:0.82em">{r["Gruppo"]}</span>'
            f'<span style="color:#00ff55;font-weight:bold;font-size:0.82em">'
            f'{r["BM_ret"]:+.1f}%</span></div>'
            for _, r in leader_df.iterrows()
        ]) or '<span style="color:#444;font-style:italic;font-size:0.80em">—</span>'

        corr_color = "#ff4422" if not all_positive else "#ffaa00"
        corr_html  = "".join([
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:3px 0;border-bottom:1px solid #1a1a1a;">'
            f'<span style="color:#aaa;font-size:0.82em">{r["Gruppo"]}</span>'
            f'<span style="color:{corr_color};font-weight:bold;font-size:0.82em">'
            f'{r["BM_ret"]:+.1f}%</span></div>'
            for _, r in corr_df.iterrows()
        ]) or '<span style="color:#444;font-style:italic;font-size:0.80em">—</span>'

        div_html = (
            "<br>".join(divergenze)
            if divergenze
            else '<span style="color:#444;font-style:italic;font-size:0.80em">'
                 'Nessuna divergenza significativa</span>'
        )

        st.markdown(
            f'<div style="background:#080808;border:1px solid #222;border-radius:10px;'
            f'padding:16px 18px;height:100%;font-family:monospace;">'
            f'<div style="border-bottom:1px solid #222;padding-bottom:10px;margin-bottom:12px;">'
            f'<div style="color:#555;font-size:0.70em;letter-spacing:0.1em;'
            f'text-transform:uppercase;">Regime tematico — {tf_label}</div>'
            f'<div style="color:{regime_color};font-size:1.25em;font-weight:bold;margin-top:4px;">'
            f'{regime_icon} {regime_txt}</div>'
            f'<div style="color:#444;font-size:0.75em;margin-top:2px;">'
            f'BM positivi: {n_bm_pos}/{n_bm_tot} &nbsp;·&nbsp; '
            f'Breadth globale: {global_breadth}% &nbsp;·&nbsp; '
            f'BM medio: {avg_bm_ret:+.1f}%</div>'
            f'</div>'
            f'<div style="margin-bottom:12px;">'
            f'<div style="color:#555;font-size:0.68em;letter-spacing:0.08em;'
            f'text-transform:uppercase;margin-bottom:4px;">{leader_title}</div>'
            f'{leader_note}'
            f'{leader_html}</div>'
            f'<div style="margin-bottom:12px;">'
            f'<div style="color:#555;font-size:0.68em;letter-spacing:0.08em;'
            f'text-transform:uppercase;margin-bottom:4px;">{corr_title}</div>'
            f'{corr_note}'
            f'{corr_html}</div>'
            f'<div>'
            f'<div style="color:#555;font-size:0.68em;letter-spacing:0.08em;'
            f'text-transform:uppercase;margin-bottom:6px;">⚡ Divergenze rilevate</div>'
            f'<div style="font-size:0.78em;line-height:1.7;">{div_html}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### 2 · Performance per timeframe")

    tf_cols    = ["1D","1W","1M","3M","6M","YTD","1A","2A"]
    disp_cols  = ["Gruppo","Ticker","Tema"] + tf_cols + ["vs BM"]

    view_df = tem_df.copy()
    if sel_sector != "TUTTI":
        view_df = view_df[view_df["Gruppo"] == sel_sector]

    view_df = view_df[disp_cols].copy()

    def highlight_best(s):
        styles = [""] * len(s)
        valid  = s.dropna()
        if valid.empty:
            return styles
        max_v = valid.max()
        min_v = valid.min()
        for i, v in enumerate(s):
            if pd.isna(v):
                styles[i] = "color:#333"
            elif v == max_v:
                styles[i] = "background-color:#003300;color:#00FF00;font-weight:bold"
            elif v == min_v:
                styles[i] = "background-color:#330000;color:#ff4422;font-weight:bold"
            elif v > 0:
                styles[i] = "color:#88cc88"
            else:
                styles[i] = "color:#cc6644"
        return styles

    def color_vs_bm(val):
        try:
            v = float(val)
            if np.isnan(v):   return "color:#333"
            if v > 2:         return "color:#00ff55;font-weight:bold"
            if v > 0:         return "color:#88cc88"
            if v > -2:        return "color:#cc6644"
            return "color:#ff4422;font-weight:bold"
        except Exception:
            return "color:#333"

    def fmt_pct(x):
        try:
            if x is None:
                return "—"
            f_val = float(x)
            if np.isnan(f_val):
                return "—"
            return f"{f_val:+.1f}%"
        except Exception:
            return "—"

    styled_tem = (
        view_df.style
        .apply(highlight_best, subset=tf_cols)
        .map(color_vs_bm, subset=["vs BM"])
        .format({c: fmt_pct for c in tf_cols + ["vs BM"]})
    )

    st.dataframe(styled_tem, use_container_width=True, hide_index=True,
                 column_config={
                     "Gruppo": st.column_config.TextColumn("Gruppo", width="medium"),
                     "Tema":   st.column_config.TextColumn("Tema",   width="medium"),
                     "vs BM":  st.column_config.TextColumn(f"vs BM ({tf_label})", width="small"),
                 })

    st.markdown(
        f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:6px;'
        f'padding:8px 16px;margin-top:4px;font-size:0.78em;color:#666;">'
        f'<b style="color:#00ff55">Verde</b> = top performer per colonna · '
        f'<b style="color:#ff4422">Rosso</b> = worst performer per colonna · '
        f'<b style="color:#ff9900">vs BM</b> = delta ritorno tematico − benchmark gruppo su {tf_label}'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown(f"### 3 · Top & Bottom 5 — {tf_label}  (tutti i gruppi)")

    ranked = tem_df.dropna(subset=[tf_label]).sort_values(tf_label, ascending=False)
    top5   = ranked.head(5)
    bot5   = ranked.tail(5).sort_values(tf_label)

    c_top, c_bot = st.columns(2)

    def mini_bar(df_slice, ascending=False, title=""):
        colors_mb = ["#00ff55" if v >= 0 else "#ff4422" for v in df_slice[tf_label]]
        fig_mb = go.Figure(go.Bar(
            x=df_slice[tf_label],
            y=df_slice["Ticker"] + " · " + df_slice["Tema"],
            orientation="h",
            marker=dict(color=colors_mb, line=dict(color="#333", width=1)),
            text=[f"{v:+.1f}%" for v in df_slice[tf_label]],
            textposition="outside",
            textfont=dict(color="white", size=10),
            hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
        ))
        fig_mb.add_vline(x=0, line_color="#444", line_width=1)
        fig_mb.update_layout(
            height=200, paper_bgcolor="#000", plot_bgcolor="#000",
            font=dict(color="white", size=9),
            title=dict(text=title, font=dict(size=11, color="#ff9900")),
            xaxis=dict(gridcolor="#111", ticksuffix="%"),
            yaxis=dict(gridcolor="#111", autorange="reversed" if not ascending else True),
            margin=dict(l=10, r=60, t=35, b=20),
            showlegend=False,
        )
        return fig_mb

    with c_top:
        st.plotly_chart(mini_bar(top5, title="🏆 Top 5"), use_container_width=True)
    with c_bot:
        st.plotly_chart(mini_bar(bot5, ascending=True, title="💀 Bottom 5"), use_container_width=True)

    st.markdown("---")
    st.markdown("### 4 · Scatter quadranti — performance assoluta vs delta benchmark")

    sc_tf_opts = ["1D","1W","1M","3M","6M","YTD","1A","2A"]
    sc_c1, sc_c2, sc_c3 = st.columns([2, 1, 1])
    with sc_c1:
        sc_tf = st.selectbox("Timeframe scatter", sc_tf_opts,
                             index=sc_tf_opts.index(tf_label), key="tem_scatter_tf")
    with sc_c2:
        label_mode = st.radio("Etichette", ["Ticker","Tema"], horizontal=True, key="tem_sc_lbl")
    with sc_c3:
        filter_scatter = st.checkbox("Solo gruppo selezionato", value=False, key="tem_sc_filter")

    rows_sc = []
    for sector, tickers, bm_ticker in TEMATICI_STRUCT:
        bm_r = np.nan
        if bm_ticker in th_prices.columns:
            bm_r = safe_ret(th_prices[bm_ticker], TF_DAYS[sc_tf])

        for ticker in tickers:
            if ticker not in th_prices.columns:
                continue
            s = th_prices[ticker].dropna()
            abs_r = safe_ret(s, TF_DAYS[sc_tf])
            if np.isnan(abs_r):
                continue
            delta = (abs_r - bm_r) if not np.isnan(bm_r) else np.nan
            rows_sc.append({
                "Gruppo":   sector,
                "Ticker":   ticker,
                "Tema":     TEMATICI_DESCRIPTIONS.get(ticker, ticker),
                "BM":       bm_ticker,
                "BM_ret":   bm_r,
                "abs_ret":  abs_r,
                "delta_bm": delta,
            })

    sc_df = pd.DataFrame(rows_sc).dropna(subset=["abs_ret","delta_bm"])

    if filter_scatter and sel_sector != "TUTTI":
        sc_df = sc_df[sc_df["Gruppo"] == sel_sector]

    if sc_df.empty:
        st.info("Dati insufficienti per lo scatter su questo timeframe.")
    else:
        group_colors = {
            s: c for s, c in zip(
                [g for g, _, _ in TEMATICI_STRUCT],
                ["#ff9900","#00ff55","#44aaff","#ff4422","#ffff44",
                 "#bb44ff","#00ffcc","#ff66cc","#88cc88","#cc8844",
                 "#4488ff","#ff8844"]
            )
        }

        fig_sc = go.Figure()

        for sector in sc_df["Gruppo"].unique():
            sub = sc_df[sc_df["Gruppo"] == sector]
            labels = sub["Ticker"] if label_mode == "Ticker" else sub["Tema"]
            color  = group_colors.get(sector, "#aaaaaa")

            hover_text = []
            for _, r in sub.iterrows():
                lbl = r["Ticker"] if label_mode == "Ticker" else r["Tema"]
                bm_str = f"{r['BM_ret']:+.1f}%" if not np.isnan(r["BM_ret"]) else "n/d"
                hover_text.append(
                    f"<b>{lbl}</b><br>"
                    f"Gruppo: {sector}<br>"
                    f"Ret {sc_tf}: {r['abs_ret']:+.1f}%<br>"
                    f"BM ({r['BM']}): {bm_str}<br>"
                    f"vs BM: {r['delta_bm']:+.1f}%"
                )

            fig_sc.add_trace(go.Scatter(
                x=sub["abs_ret"],
                y=sub["delta_bm"],
                mode="markers+text",
                name=sector,
                marker=dict(size=10, color=color, opacity=0.85,
                            line=dict(color="#111", width=1)),
                text=labels,
                textposition="top center",
                textfont=dict(size=8, color="#cccccc"),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover_text,
            ))

        fig_sc.add_hline(y=0, line_color="#333", line_width=1.5)
        fig_sc.add_vline(x=0, line_color="#333", line_width=1.5)

        pad_x = (sc_df["abs_ret"].max() - sc_df["abs_ret"].min()) * 0.08
        pad_y = (sc_df["delta_bm"].max() - sc_df["delta_bm"].min()) * 0.08
        q_x_pos = sc_df["abs_ret"].max()  - pad_x
        q_x_neg = sc_df["abs_ret"].min()  + pad_x
        q_y_pos = sc_df["delta_bm"].max() - pad_y
        q_y_neg = sc_df["delta_bm"].min() + pad_y

        quadrants = [
            (q_x_pos, q_y_pos, "LEADER",     "#00ff55", "top right"),
            (q_x_neg, q_y_pos, "ALPHA PURO", "#44aaff", "top left"),
            (q_x_pos, q_y_neg, "BETA PURO",  "#ffaa00", "bottom right"),
            (q_x_neg, q_y_neg, "EVITARE",    "#ff4422", "bottom left"),
        ]
        for qx, qy, qlabel, qcolor, qanchor in quadrants:
            fig_sc.add_annotation(
                x=qx, y=qy, text=qlabel, showarrow=False,
                font=dict(color=qcolor, size=10, family="Courier New"),
                opacity=0.45, xanchor=qanchor.split()[1], yanchor=qanchor.split()[0]
            )

        fig_sc.update_layout(
            height=500,
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            font=dict(color="white", size=10),
            title=dict(
                text=(f"Scatter {sc_tf} — asse X: ritorno assoluto  |  asse Y: delta vs benchmark gruppo"),
                font=dict(size=10, color="#666")
            ),
            xaxis=dict(title=f"Ritorno assoluto {sc_tf} (%)", gridcolor="#1a1a1a",
                       ticksuffix="%", zeroline=False),
            yaxis=dict(title=f"Delta vs benchmark ({sc_tf}) %", gridcolor="#1a1a1a",
                       ticksuffix="%", zeroline=False),
            legend=dict(font=dict(size=8), bgcolor="rgba(0,0,0,0.5)",
                        bordercolor="#333", borderwidth=1,
                        orientation="v", x=1.01, y=1),
            margin=dict(l=60, r=160, t=50, b=60),
            hoverlabel=dict(bgcolor="#111", font_size=11),
        )
        st.plotly_chart(fig_sc, use_container_width=True)

        st.markdown("""
        <div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;
                    padding:10px 20px;margin-top:4px;font-size:0.80em;color:#888;
                    display:flex;gap:24px;flex-wrap:wrap;">
            <span><b style="color:#00ff55">LEADER</b> — ritorno positivo E sovraperforma il benchmark</span>
            <span><b style="color:#44aaff">ALPHA PURO</b> — ritorno negativo ma batte il benchmark</span>
            <span><b style="color:#ffaa00">BETA PURO</b> — ritorno positivo ma sotto il benchmark</span>
            <span><b style="color:#ff4422">EVITARE</b> — ritorno negativo E sottoperforma il benchmark</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#0a0a0a;border:1px solid #1a1a1a;border-radius:8px;
                padding:10px 20px;margin-top:16px;font-size:0.78em;color:#555;">
        <b style="color:#ff9900">vs BM</b> = differenza ritorno tematico − ritorno benchmark di gruppo (stesso TF)
    </div>
    """, unsafe_allow_html=True)


# ========================
# TAB 8 — BACKTEST RS
# ========================
with tab8:
    import json

    st.markdown(
        '<h3 style="color:#ff9900;margin-bottom:4px;">🧪 Backtest Rotation Score — Episodi Risk Off</h3>'
        '<p style="color:#555;font-size:0.82em;margin-top:0;">'
        'Dataset storico 2021–2026 · 5 episodi identificati · Soglia dinamica ~-3.5 · Conferma 5 giorni</p>',
        unsafe_allow_html=True
    )

    try:
        with open("backtest_patterns.json", "r", encoding="utf-8") as f:
            bt = json.load(f)
        bt_ok = True
    except FileNotFoundError:
        st.warning("⚠️ File backtest_patterns.json non trovato nel repo.")
        bt_ok = False
    except Exception as e:
        st.error(f"Errore lettura backtest_patterns.json: {e}")
        bt_ok = False

    if bt_ok:

        stats = bt["statistiche_aggregate"]
        k1, k2, k3, k4, k5 = st.columns(5)
        kpi_bt = [
            (k1, "Win Rate",           stats["win_rate"],                              "#00ff55"),
            (k2, "Payoff medio +40gg", f"+{stats['spy_perf_40_media_positivi']:.1f}%", "#00ff55"),
            (k3, "Payoff medio +20gg", f"+{stats['spy_perf_20_media_positivi']:.1f}%", "#88cc88"),
            (k4, "Durata media ep.",   f"{stats['durata_media_gg']:.0f} gg",           "#ff9900"),
            (k5, "RS min medio",       f"{stats['rs_min_medio']:.2f}",                 "#ff4422"),
        ]
        for col, label, val, color in kpi_bt:
            col.markdown(
                f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;'
                f'padding:10px 14px;margin-bottom:10px;">'
                f'<div style="color:#555;font-size:0.72em;letter-spacing:0.06em">{label}</div>'
                f'<div style="color:{color};font-size:1.15em;font-weight:bold">{val}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown(
            f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:6px;'
            f'padding:8px 16px;margin-bottom:16px;font-size:0.80em;color:#666;">'
            f'⏱ <b style="color:#ff9900">Timing critico</b>: {bt["statistiche_aggregate"]["nota_timing"]}'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown("### 📋 Regole operative")
        ro = bt["regola_operativa"]
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown(
                f'<div style="background:#0d2b0d;border:1px solid #00cc44;border-radius:8px;'
                f'padding:14px 16px;">'
                f'<div style="color:#00ff55;font-size:0.72em;letter-spacing:0.08em;'
                f'text-transform:uppercase;margin-bottom:6px;">✅ Segnale POSITIVO</div>'
                f'<div style="color:#ccc;font-size:0.85em;line-height:1.6;">{ro["segnale_positivo"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col_r2:
            st.markdown(
                f'<div style="background:#2b0d0d;border:1px solid #cc2200;border-radius:8px;'
                f'padding:14px 16px;">'
                f'<div style="color:#ff4422;font-size:0.72em;letter-spacing:0.08em;'
                f'text-transform:uppercase;margin-bottom:6px;">❌ Segnale NEGATIVO</div>'
                f'<div style="color:#ccc;font-size:0.85em;line-height:1.6;">{ro["segnale_negativo"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("### 1 · Episodi storici")

        colori_pattern = {"A": "#ff4422", "B": "#ffaa00", "C": "#44aaff", "D": "#ffff44"}
        colori_esito   = {
            "positivo_forte": "#00ff55",
            "positivo":       "#88cc88",
            "positivo_lento": "#ffaa00",
            "negativo":       "#ff4422",
        }

        rows_bt = []
        for ep in bt["episodi"]:
            ind = ep["indicatori"]
            top = ep["top_successivo"]
            rows_bt.append({
                "Ep":           ep["id"],
                "Pattern":      ep["pattern"],
                "RS inizio":    ep["rs_inizio"],
                "RS bottom":    ep["rs_bottom_date"],
                "RS min":       ep["rs_min"],
                "Durata (gg)":  ep["durata_gg"],
                "SPY bottom":   ep["spy_bottom_date"],
                "Δ RS→SPY(gg)": ep["delta_rs_spy_gg"],
                "SPY +20gg":    ep["spy_perf_20"],
                "SPY +40gg":    ep["spy_perf_40"],
                "VIX":          ind["vix"],
                "MOVE":         ind["move"] if ind["move"] else "n/d",
                "IEF-SHY":      ind["ief_shy"],
                "Top qualità":  top["qualita"],
                "Esito":        ep["esito"],
            })

        bt_df = pd.DataFrame(rows_bt)

        def style_pattern_col(val):
            c = colori_pattern.get(str(val), "#888")
            return f"color:{c};font-weight:bold"

        def style_esito_col(val):
            c = colori_esito.get(str(val), "#888")
            return f"color:{c};font-weight:bold"

        def style_delta(val):
            try:
                v = float(val)
                if v < 0:  return "color:#44aaff;font-weight:bold"
                if v > 40: return "color:#ff4422"
                return "color:#888"
            except Exception:
                return ""

        def style_rs_min_bt(val):
            try:
                v = float(val)
                if v < -8: return "color:#ff4422;font-weight:bold"
                if v < -6: return "color:#ffaa00;font-weight:bold"
                return "color:#888"
            except Exception:
                return ""

        def style_top_qualita(val):
            if str(val) == "VERO":    return "color:#00ff55;font-weight:bold"
            if str(val) == "TECNICO": return "color:#ffaa00;font-weight:bold"
            return ""

        st.dataframe(
            bt_df.style
                .map(style_pattern_col,  subset=["Pattern"])
                .map(style_esito_col,    subset=["Esito"])
                .map(style_delta,        subset=["Δ RS→SPY(gg)"])
                .map(style_rs_min_bt,    subset=["RS min"])
                .map(style_top_qualita,  subset=["Top qualità"])
                .format({
                    "RS min":    "{:.2f}",
                    "SPY +20gg": "{:+.2f}%",
                    "SPY +40gg": "{:+.2f}%",
                    "IEF-SHY":   "{:.2f}",
                }),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")
        st.markdown("### 2 · Pattern di riferimento")

        pattern_cols = st.columns(4)
        pattern_order = ["A", "B", "C", "D"]
        for i, pid in enumerate(pattern_order):
            p = bt["pattern"][pid]
            cond = p["condizioni"]
            cond_str = " · ".join([f"{k.upper()} {v}" for k, v in cond.items()])
            color = colori_pattern[pid]
            with pattern_cols[i]:
                st.markdown(
                    f'<div style="background:#0d0d0d;border:1px solid {color}33;'
                    f'border-top:3px solid {color};border-radius:8px;padding:14px;height:100%;">'
                    f'<div style="color:{color};font-size:1.1em;font-weight:bold;'
                    f'margin-bottom:6px;">Pattern {pid}</div>'
                    f'<div style="color:#ff9900;font-size:0.82em;font-weight:bold;'
                    f'margin-bottom:8px;">{p["nome"]}</div>'
                    f'<div style="color:#555;font-size:0.72em;margin-bottom:8px;">{cond_str}</div>'
                    f'<div style="color:#aaa;font-size:0.78em;line-height:1.5;'
                    f'margin-bottom:8px;">{p["descrizione"]}</div>'
                    f'<div style="color:{color};font-size:0.75em;font-style:italic;">'
                    f'↗ {p["payoff_atteso"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("---")
        st.markdown("### 3 · Note analitiche per episodio")

        for ep in bt["episodi"]:
            color = colori_pattern.get(ep["pattern"], "#888")
            esito_color = colori_esito.get(ep["esito"], "#888")
            with st.expander(
                f"Ep.{ep['id']} — {ep['rs_inizio']}  |  Pattern {ep['pattern']}  |  "
                f"RS min: {ep['rs_min']}  |  SPY +40gg: {ep['spy_perf_40']:+.2f}%",
                expanded=False
            ):
                st.markdown(
                    f'<div style="background:#080808;border-left:3px solid {color};'
                    f'padding:12px 16px;border-radius:0 6px 6px 0;'
                    f'font-size:0.85em;color:#aaa;line-height:1.7;">'
                    f'{ep["note"]}'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("---")
        st.markdown("### 4 · Regola qualità top")
        rqt = bt["regola_qualita_top"]
        st.markdown(
            f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;'
            f'padding:14px 20px;font-size:0.85em;line-height:1.8;">'
            f'<b style="color:#00ff55">Top VERO</b>: {rqt["top_vero"]}<br>'
            f'<b style="color:#ffaa00">Top TECNICO</b>: {rqt["top_tecnico"]}<br>'
            f'<span style="color:#555">{rqt["implicazione"]}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            f'<div style="background:#0a0a0a;border:1px solid #1a1a1a;border-radius:6px;'
            f'padding:8px 16px;margin-top:16px;font-size:0.75em;color:#444;">'
            f'📅 Dati aggiornati al: <b style="color:#ff9900">{bt["metadata"]["aggiornato"]}</b> · '
            f'Per aggiornare: modifica <b>backtest_patterns.json</b> nel repo e fai commit'
            f'</div>',
            unsafe_allow_html=True
        )

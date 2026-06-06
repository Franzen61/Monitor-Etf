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



WEIGHTS = {"1M":0.30,"3M":0.40,"6M":0.30}
# ========================
# EUROSTOXX 600
# ========================
EURO_SECTORS = [
    "EXH1.DE","EXV6.DE","EXV7.DE","EXV3.DE","EXH4.DE",
    "EXV1.DE","EXH2.DE","EXH9.DE","EXH5.DE","EXV8.DE",
    "EXH6.DE","EXV4.DE","EXV5.DE","EXH8.DE","EXV9.DE",
    "EXI5.DE","EXH3.DE","EXH7.DE","EXV2.DE",
]
EURO_BENCHMARK = "EXSA.DE"
EURO_ALL = EURO_SECTORS + [EURO_BENCHMARK]
EURO_NAMES = {
    "EXH1.DE":"Oil & Gas",      "EXV6.DE":"Basic Res.",
    "EXV7.DE":"Chemicals", "EXV3.DE":"Technology",
    "EXH4.DE":"Industrials",     "EXV1.DE":"Banks",
    "EXH2.DE":"Financial Svcs",  "EXH9.DE":"Utilities",
    "EXH5.DE":"Insurance",       "EXV8.DE":"Constr & Mat",
    "EXH6.DE":"Media",  "EXV4.DE":"Healthcare",
    "EXV5.DE":"Automobiles",     "EXH8.DE":"Retail",
    "EXV9.DE":"Travel & Leisure","EXI5.DE":"Real Estate",
    "EXH3.DE":"Food & Bev",      "EXH7.DE":"Personal & Hous",
    "EXV2.DE":"Telecom",    "EXSA.DE":"STOXX 600",
}

# ── ROS 2.0 weights (Intervento 1)
WEIGHTS_V2 = {"1W": 0.15, "1M": 0.25, "3M": 0.35, "6M": 0.25}

# ── Vol Confirmation score map (Intervento 3)
VOL_SCORE_MAP = {
    "[B+M+] ACCUMULO":   +1.0,
    "[B+M-] INVERSIONE": +0.3,
    "[B~ M~] INDECISO":   0.0,
    "[B-M+] ESAURIM.":   -0.3,
    "[B-M-] DISTRIBUZ":  -1.0,
}


TF_DAYS = {"1D": 1, "1W": 5, "1M": 21, "3M": 63, "6M": 126, "YTD": None, "1A": 252, "2A": 504}

# ========================
# DATA LOADERS
# ========================
@st.cache_data(ttl=60*60)
def load_prices(tickers):
    end = datetime.today()
    start = end - timedelta(days=6*365)
    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"]
    else:
        close = data
    return close.dropna(how="all")


# ── FIX: load_prices_today con TTL 5 min per dati 1D sempre freschi
@st.cache_data(ttl=5*60)
def load_prices_today(tickers):
    """
    Scarica solo gli ultimi 7 giorni con TTL 5 min.
    Usata esclusivamente per il calcolo 1D — evita lag post-chiusura yfinance.
    """
    end   = datetime.today()
    start = end - timedelta(days=7)
    data  = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"]
    else:
        close = data
    return close.dropna(how="all")


@st.cache_data(ttl=60*60)
def load_ohlcv(tickers):
    end = datetime.today()
    start = end - timedelta(days=90)
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    return raw


@st.cache_data(ttl=60*60)
def load_ohlcv_long(tickers):
    end   = datetime.today()
    start = end - timedelta(days=2*365)
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    return raw


# ── FIX: Wikipedia con StringIO + fallback robusto
@st.cache_data(ttl=60*60*6)
def load_sp500_data(timeframe_days: int):
    import requests
    from io import StringIO
    wiki, resp = None, None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers=headers, timeout=15
        )
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text), attrs={"id": "constituents"})
        if tables:
            raw     = tables[0]
            sym_col = next((c for c in raw.columns if "Symbol" in str(c) or "Ticker" in str(c)), None)
            sec_col = next((c for c in raw.columns if "Sector" in str(c) or "GICS"   in str(c)), None)
            if sym_col and sec_col:
                wiki = raw[[sym_col, sec_col]].copy()
                wiki.columns = ["Ticker", "Sector"]
                wiki["Ticker"] = wiki["Ticker"].astype(str).str.replace(".", "-", regex=False)
    except Exception:
        pass
    if wiki is None and resp is not None:
        try:
            from io import StringIO as _SIO
            tables  = pd.read_html(_SIO(resp.text), header=0)
            raw     = tables[0]
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
    tickers    = wiki["Ticker"].tolist()
    fetch_days = timeframe_days + 15
    end        = datetime.today()
    start      = end - timedelta(days=fetch_days)
    try:
        raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False, threads=True)
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
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
        idx     = min(timeframe_days, len(series) - 1)
        ret_val = (series.iloc[-1] / series.iloc[-idx] - 1) * 100
        results.append({"Ticker": ticker, "Return": round(ret_val, 2)})
    ret_df = pd.DataFrame(results)
    merged = ret_df.merge(wiki, on="Ticker", how="left").dropna(subset=["Sector"])
    return merged



# ========================
# VOLUME SIGNAL (VWDS)
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
        idx = hi.index.intersection(lo.index).intersection(cl.index).intersection(vo.index)
        hi, lo, cl, vo = hi[idx].iloc[-window:], lo[idx].iloc[-window:], cl[idx].iloc[-window:], vo[idx].iloc[-window:]
        if len(cl) < max(3, window // 3):
            return np.nan
        prev_cl        = cl.shift(1)
        pct_chg        = (cl - prev_cl) / prev_cl.replace(0, np.nan)
        direction      = np.sign(cl - prev_cl)
        strength       = pct_chg.abs().clip(upper=0.05)
        dir_signal     = direction * strength
        max_strength   = strength.max()
        dir_signal_norm = pd.Series(0.0, index=dir_signal.index) if (pd.isna(max_strength) or max_strength == 0) \
                          else (dir_signal / max_strength).fillna(0.0)
        buy_vol_dir    = vo * dir_signal_norm.clip(lower=0)
        sell_vol_dir   = vo * dir_signal_norm.clip(upper=0).abs()
        rng            = (hi - lo).replace(0, np.nan)
        pos_signal     = ((cl - lo) / rng).fillna(0.5).clip(0, 1)
        pos_signal     = (pos_signal - 0.5) * 2
        buy_vol_pos    = vo * pos_signal.clip(lower=0)
        sell_vol_pos   = vo * pos_signal.clip(upper=0).abs()
        buy_total      = (w_dir * buy_vol_dir  + w_pos * buy_vol_pos).sum()
        sell_total     = (w_dir * sell_vol_dir + w_pos * sell_vol_pos).sum()
        total          = buy_total + sell_total
        if total == 0 or pd.isna(total):
            return np.nan
        return round(float((buy_total - sell_total) / total), 3)
    except Exception:
        return np.nan


def volume_signal(score_short, score_medium):
    THRESHOLD = 0.05
    def is_pos(s): return s is not None and not np.isnan(s) and s >  THRESHOLD
    def is_neg(s): return s is not None and not np.isnan(s) and s < -THRESHOLD
    sq_green  = '<span class="vol-square vol-green">✓</span>'
    sq_red    = '<span class="vol-square vol-red">✗</span>'
    sq_yellow = '<span class="vol-square vol-yellow">~</span>'
    sq_s = sq_green if is_pos(score_short)  else sq_red if is_neg(score_short)  else sq_yellow
    sq_m = sq_green if is_pos(score_medium) else sq_red if is_neg(score_medium) else sq_yellow
    if   is_pos(score_short) and is_pos(score_medium):
        label, css_label = "CONFERMATO",         "vol-label-confirmed"
        sublabel, text_plain = "Volume in accumulo su entrambi i timeframe", "[B+M+] ACCUMULO"
    elif is_neg(score_short) and is_neg(score_medium):
        label, css_label = "DISTRIBUZIONE",      "vol-label-distribution"
        sublabel, text_plain = "Pressione vendita dominante — cautela", "[B-M-] DISTRIBUZ"
    elif is_pos(score_short) and is_neg(score_medium):
        label, css_label = "INVERSIONE IN CORSO","vol-label-reversal"
        sublabel, text_plain = "Breve si rafforza su medio debole — monitorare", "[B+M-] INVERSIONE"
    elif is_neg(score_short) and is_pos(score_medium):
        label, css_label = "ESAURIMENTO",        "vol-label-exhaustion"
        sublabel, text_plain = "Breve si deteriora su medio positivo — attenzione", "[B-M+] ESAURIM."
    else:
        label, css_label = "INDECISO",           "vol-label-neutral"
        sublabel, text_plain = "Segnale volumetrico non direzionale", "[B~ M~] INDECISO"
    html_badge = (
        f'{sq_s}&nbsp;{sq_m}&nbsp;<span class="{css_label}">{label}</span>'
        f'<br><span class="vol-sublabel">{sublabel}</span>'
    )
    return html_badge, text_plain


# ========================
# ENHANCED OBV FLOW
# ========================
def compute_obv_flow(close: pd.Series, volume: pd.Series,
                     len_vol: int = 20, len_ema: int = 13,
                     len_cci: int = 20, len_trend: int = 50) -> dict:
    close  = close.dropna()
    volume = volume.dropna()
    idx    = close.index.intersection(volume.index)
    close, volume = close[idx], volume[idx]
    if len(close) < max(len_vol, len_trend) + 5:
        empty = pd.Series(dtype=float)
        return {k: empty for k in ["flow_cum","flow_ema","flow_trend","cci_flow","cci_scaled"]}
    avg_vol   = volume.rolling(len_vol, min_periods=len_vol // 2).mean()
    norm_vol  = volume / avg_vol.replace(0, np.nan)
    chg       = close.diff()
    direction = np.sign(chg).fillna(0)
    flow_cum  = (direction * norm_vol).fillna(0).cumsum()
    flow_ema  = flow_cum.ewm(span=len_ema, adjust=False).mean()
    flow_trend= flow_ema.rolling(len_trend, min_periods=len_trend // 2).mean()
    flow_ema_sma = flow_ema.rolling(len_cci, min_periods=len_cci // 2).mean()
    flow_ema_std = flow_ema.rolling(len_cci, min_periods=len_cci // 2).std()
    mean_dev  = flow_ema.rolling(len_cci, min_periods=len_cci // 2).apply(
        lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
    ).replace(0, np.nan)
    cci_flow  = (flow_ema - flow_ema_sma) / (0.015 * mean_dev)
    cci_sma   = cci_flow.rolling(len_cci, min_periods=len_cci // 2).mean()
    cci_std   = cci_flow.rolling(len_cci, min_periods=len_cci // 2).std().replace(0, np.nan)
    cci_z     = (cci_flow - cci_sma) / cci_std
    flow_std  = flow_ema_std.replace(0, np.nan)
    cci_scaled= flow_ema_sma + cci_z * flow_std * 0.5
    return {"flow_cum": flow_cum, "flow_ema": flow_ema, "flow_trend": flow_trend,
            "cci_flow": cci_flow, "cci_scaled": cci_scaled}


def obv_flow_regime(close: pd.Series, volume: pd.Series,
                    len_vol: int = 20, len_ema: int = 13,
                    len_cci: int = 20, len_trend: int = 50) -> str:
    result = compute_obv_flow(close, volume, len_vol, len_ema, len_cci, len_trend)
    fe, ft = result["flow_ema"], result["flow_trend"]
    if fe.empty or ft.empty:
        return "N/D"
    last_fe, last_ft = fe.dropna(), ft.dropna()
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
# ROTATION SCORE v1 (originale — usata in Tab8/Backtest)
# ========================
def compute_rotation_score_series(prices):
    ret_1m = prices.pct_change(21,  fill_method=None)
    ret_3m = prices.pct_change(63,  fill_method=None)
    ret_6m = prices.pct_change(126, fill_method=None)
    rar_1m = ret_1m.sub(ret_1m[BENCHMARK], axis=0)
    rar_3m = ret_3m.sub(ret_3m[BENCHMARK], axis=0)
    rar_6m = ret_6m.sub(ret_6m[BENCHMARK], axis=0)
    rar_mean = (rar_1m + rar_3m + rar_6m) / 3
    cyc  = rar_mean[CYCLICAL].mean(axis=1)
    def_ = rar_mean[DEFENSIVE].mean(axis=1)
    return (cyc - def_) * 100


# ========================
# ROTATION SCORE v2 — ROS 2.0 (Intervento 1)
# ========================
def compute_rotation_score_series_v2(prices):
    ret_1w  = prices.pct_change(5,   fill_method=None)
    ret_1m  = prices.pct_change(21,  fill_method=None)
    ret_3m  = prices.pct_change(63,  fill_method=None)
    ret_6m  = prices.pct_change(126, fill_method=None)
    rar_1w  = ret_1w.sub(ret_1w[BENCHMARK], axis=0)
    rar_1m  = ret_1m.sub(ret_1m[BENCHMARK], axis=0)
    rar_3m  = ret_3m.sub(ret_3m[BENCHMARK], axis=0)
    rar_6m  = ret_6m.sub(ret_6m[BENCHMARK], axis=0)
    rar_w   = (rar_1w * WEIGHTS_V2["1W"] + rar_1m * WEIGHTS_V2["1M"] +
               rar_3m * WEIGHTS_V2["3M"] + rar_6m * WEIGHTS_V2["6M"])
    cyc  = rar_w[CYCLICAL].mean(axis=1)
    def_ = rar_w[DEFENSIVE].mean(axis=1)
    return (cyc - def_) * 100


# ========================
# ADAPTIVE THRESHOLD — Intervento 2
# ========================
def compute_adaptive_threshold(series, window=252, multiplier=0.75):
    rolling_std = series.rolling(window=window, min_periods=63).std()
    return (rolling_std * multiplier).dropna()


# ========================
# VOL CONFIRMATION — Intervento 3
# ========================
def compute_vol_confirmation(vol_plain_dict, cyclicals, defensives):
    cyc_scores = [VOL_SCORE_MAP.get(vol_plain_dict.get(t, "[B~ M~] INDECISO"), 0.0) for t in cyclicals]
    def_scores = [VOL_SCORE_MAP.get(vol_plain_dict.get(t, "[B~ M~] INDECISO"), 0.0) for t in defensives]
    return round(float(np.mean(cyc_scores)) - float(np.mean(def_scores)), 3)

def compute_vol_multiplier(vol_confirmation):
    if vol_confirmation >= 0.5:  return 1.0
    elif vol_confirmation >= 0.0: return 0.75
    else:                         return 0.5


# ========================
# INT.4 — DERIVATA BANDA ADATTIVA
# ========================
def compute_band_derivative(adaptive_threshold_series, window=10):
    import math
    if adaptive_threshold_series.empty or len(adaptive_threshold_series) < window + 2:
        return pd.Series(dtype=float), {
            "deriv": float("nan"), "stato": "N/D", "color": "#888888",
            "soglia_stretta": float("nan"), "soglia_larga": float("nan"), "deriv_std": float("nan"),
        }
    deriv     = adaptive_threshold_series.pct_change(window).dropna() * 100
    deriv_std = float(deriv.std())
    s_str, s_lar = -0.5 * deriv_std, 0.5 * deriv_std
    deriv_now = float(deriv.iloc[-1]) if not deriv.empty else float("nan")
    if math.isnan(deriv_now):          stato, color = "N/D",            "#888888"
    elif deriv_now < s_str * 2:        stato, color = "STRETTA RAPIDA", "#ff4422"
    elif deriv_now < s_str:            stato, color = "STRETTA",        "#ffaa00"
    elif deriv_now > s_lar * 2:        stato, color = "LARGA RAPIDA",   "#44aaff"
    elif deriv_now > s_lar:            stato, color = "LARGA",          "#888888"
    else:                              stato, color = "STABILE",        "#aaaaaa"
    return deriv, {"deriv": deriv_now, "stato": stato, "color": color,
                   "soglia_stretta": s_str, "soglia_larga": s_lar, "deriv_std": deriv_std}


# ========================
# RISK OFF EPISODES
# ========================
def compute_risk_off_episodes(series, threshold, confirm_days=3):
    if series.empty:
        return []
    neg_threshold = -abs(threshold)
    episodes, in_episode, ep_start, ep_confirmed = [], False, None, None
    consec_below, consec_above = 0, 0
    for date, val in series.items():
        is_below = val < neg_threshold
        if not in_episode:
            if is_below:
                consec_below += 1
                if consec_below == 1:
                    ep_start = date
                if consec_below >= confirm_days:
                    in_episode, ep_confirmed, consec_above = True, date, 0
            else:
                consec_below, ep_start = 0, None
        else:
            if not is_below:
                consec_above += 1
                if consec_above >= confirm_days:
                    ep_slice = series[ep_start:date]
                    episodes.append({"start": ep_start, "confirmed": ep_confirmed, "end": date,
                                     "open": False, "duration": (date - ep_start).days,
                                     "rs_min": round(float(ep_slice.min()), 2), "rs_min_date": ep_slice.idxmin()})
                    in_episode, consec_below, consec_above, ep_start = False, 0, 0, None
            else:
                consec_above = 0
    if in_episode and ep_start is not None:
        ep_slice = series[ep_start:]
        episodes.append({"start": ep_start, "confirmed": ep_confirmed, "end": None, "open": True,
                          "duration": (series.index[-1] - ep_start).days,
                          "rs_min": round(float(ep_slice.min()), 2), "rs_min_date": ep_slice.idxmin()})
    return episodes

# ========================
# EUROSTOXX LOADERS
# ========================
@st.cache_data(ttl=3600)
def load_euro_prices():
    end   = datetime.today()
    start = end - timedelta(days=2*365+30)
    raw   = yf.download(EURO_ALL, start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    return close.dropna(how="all")

@st.cache_data(ttl=300)
def load_euro_prices_today():
    end   = datetime.today()
    start = end - timedelta(days=7)
    raw   = yf.download(EURO_ALL, start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    return close.dropna(how="all")

# ========================
# EUROSTOXX INDICATORS
# ========================
def compute_euro_indicators(prices, today_prices, benchmark):
    results = []
    bm  = prices[benchmark].dropna() if benchmark in prices.columns else None
    bm_t= today_prices[benchmark].dropna() if benchmark in today_prices.columns else None
    wts = [0.20, 0.35, 0.25, 0.20]

    def get_rsr(tk, days):
        try:
            s = today_prices[tk].dropna() if days==1 else prices[tk].dropna()
            b = bm_t if days==1 else bm
            if s is None or b is None or len(s)<=days or len(b)<=days: return np.nan
            rs = float(s.iloc[-1]/s.iloc[-days-1]-1)
            rb = float(b.iloc[-1]/b.iloc[-days-1]-1)
            return float((1+rs)/(1+rb)-1)
        except: return np.nan

    def get_abs(tk, days):
        try:
            s = prices[tk].dropna()
            if len(s)<=days: return np.nan
            return float(s.iloc[-1]/s.iloc[-days-1]-1)
        except: return np.nan

    for tk in [t for t in prices.columns if t != benchmark]:
        r1d=get_rsr(tk,1); r1w=get_rsr(tk,5)
        r1m=get_rsr(tk,21); r3m=get_rsr(tk,63); r6m=get_rsr(tk,126)
        vals_r=[r1w,r1m,r3m,r6m]
        mms6m_rsr = sum(v*w for v,w in zip(vals_r,wts)) if not any(np.isnan(v) for v in vals_r) else np.nan
        vals_a=[get_abs(tk,d) for d in [5,21,63,126]]
        mms6m_abs = sum(v*w for v,w in zip(vals_a,wts)) if not any(np.isnan(v) for v in vals_a) else np.nan
        breve = r1m*0.50+r1w*0.35+r1d*0.15 if not any(np.isnan(v) for v in [r1m,r1w,r1d]) else np.nan
        medio = r1m*0.35+r3m*0.25+r6m*0.20+r1w*0.20 if not any(np.isnan(v) for v in [r1m,r3m,r6m,r1w]) else np.nan
        tt  = (breve-medio) if (not np.isnan(breve) and not np.isnan(medio)) else np.nan
        mr  = (breve/(abs(medio)+2)) if (not np.isnan(breve) and not np.isnan(medio)) else np.nan
        if not np.isnan(mms6m_rsr) and mms6m_rsr>0.03 and not np.isnan(r1w) and not np.isnan(r1m):
            mbi = ((r1w+r1m)/2 - mms6m_rsr) / abs(mms6m_rsr)
        else:
            mbi = np.nan

        results.append({
            "Ticker":tk, "Nome":EURO_NAMES.get(tk,tk),
            "RSr 1D":r1d, "RSr 1W":r1w, "RSr 1M":r1m, "RSr 3M":r3m, "RSr 6M":r6m,
            "MMS6M RSr":mms6m_rsr, "MMS6M Ass.":mms6m_abs,
            "Tact. Thrust":tt, "Mr Index":mr, "MBI":mbi,
        })
    return pd.DataFrame(results).set_index("Ticker")
def calcola_maxdd_assoluto(ticker, bt_close, actual_ref, periodo_giorni=63):
    try:
        tk_s = bt_close[ticker].dropna()
        end_idx   = tk_s.index.searchsorted(actual_ref)
        start_idx = max(0, end_idx - periodo_giorni)
        tk_win = tk_s.iloc[start_idx:end_idx]
        if len(tk_win) < 10: return np.nan
        rolling_max = tk_win.expanding().max()
        drawdown = (tk_win - rolling_max) / rolling_max
        return float(drawdown.min())
    except: return np.nan
def calcola_maxdd_rsr(ticker, benchmark, bt_close, actual_ref, periodo_giorni=63):
    try:
        tk_s = bt_close[ticker].dropna()
        bm_s = bt_close[benchmark].dropna()
        end_idx   = tk_s.index.searchsorted(actual_ref)
        start_idx = max(0, end_idx - periodo_giorni)
        tk_win = tk_s.iloc[start_idx:end_idx]
        bm_win = bm_s.reindex(tk_win.index).dropna()
        tk_win = tk_win.reindex(bm_win.index)
        if len(tk_win) < 10: return np.nan
        rsr_s = (tk_win / bm_win) - 1
        rolling_max = rsr_s.expanding().max()
        drawdown    = rsr_s - rolling_max
        return float(drawdown.min())
    except: return np.nan
def calcola_maxdd_assoluto_6m(ticker, bt_close, actual_ref, periodo_giorni=126):
    try:
        tk_s = bt_close[ticker].dropna()
        end_idx   = tk_s.index.searchsorted(actual_ref)
        start_idx = max(0, end_idx - periodo_giorni)
        tk_win = tk_s.iloc[start_idx:end_idx]
        if len(tk_win) < 10: return np.nan
        rolling_max = tk_win.expanding().max()
        drawdown = (tk_win - rolling_max) / rolling_max
        return float(drawdown.min())
    except: return np.nan
# ========================
# LOAD SECTORAL DATA
# ========================
prices       = load_prices(ALL_TICKERS)          # storico lungo, TTL 1h
prices_today = load_prices_today(ALL_TICKERS)    # ultimi 7gg, TTL 5min — per 1D fresco
ohlcv_long   = load_ohlcv_long(tuple(ALL_TICKERS))
ohlcv        = ohlcv_long                        # usato da VWDS (90gg sufficienti, inclusi in 2A)

# Il calcolo 1D usa prices_today (fresco). 1W/1M/3M/6M usano prices (storico lungo).
returns = pd.DataFrame({
    "1D": prices_today.apply(lambda x: ret(x, 1)),
    "1W": prices.apply(lambda x: ret(x, 5)),
    "1M": prices.apply(lambda x: ret(x, 21)),
    "3M": prices.apply(lambda x: ret(x, 63)),
    "6M": prices.apply(lambda x: ret(x, 126)),
})

rsr_df = pd.DataFrame(index=returns.index, columns=returns.columns)
for col in returns.columns:
    rsr_df[col] = rsr(returns[col], returns.loc[BENCHMARK, col])

df = rsr_df.loc[SECTORS].copy()
df["Rsr_momentum"]  = df["1M"] * WEIGHTS["1M"] + df["3M"] * WEIGHTS["3M"] + df["6M"] * WEIGHTS["6M"]
df["Coerenza_Trend"]= df[["1D","1W","1M","3M","6M"]].gt(0).sum(axis=1)
df["Delta_RS_5D"]   = df["1W"]
df = df.sort_values("Rsr_momentum", ascending=False)
df["Classifica"]    = range(1, len(df)+1)

def situazione(row):
    if row.Rsr_momentum > 0:
        return "LEADER" if row.Coerenza_Trend >= 4 else "IN RECUPERO"
    return "DEBOLE"
df["Situazione"] = df.apply(situazione, axis=1)

def operativita(row):
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4 and row["Delta_RS_5D"] > 0: return "🔥 LEADER"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4:                             return "📈 HOLD"
    if row["Classifica"] > 3  and row["Coerenza_Trend"] >= 4:                             return "👀 OSSERVARE"
    return "❌ EVITARE"
df["Operatività"] = df.apply(operativita, axis=1)

# ========================
# VOLUME SIGNAL
# ========================
vol_html, vol_plain, _vol_errors = {}, {}, []
for ticker in SECTORS + [BENCHMARK]:
    s_short  = compute_vwds(ohlcv, ticker, window=10)
    s_medium = compute_vwds(ohlcv, ticker, window=20)
    if np.isnan(s_short) and np.isnan(s_medium):
        _vol_errors.append(ticker)
    h, p = volume_signal(s_short, s_medium)
    vol_html[ticker], vol_plain[ticker] = h, p
if _vol_errors:
    st.sidebar.warning(f"⚠️ Volume Signal non disponibile per: {', '.join(_vol_errors)}.")
df["Vol Signal"] = df.index.map(vol_plain)

# ========================
# OBV FLOW REGIME
# ========================
obv_regime     = {}
_obv_available = list(ohlcv_long["Close"].columns) if isinstance(ohlcv_long.columns, pd.MultiIndex) else [BENCHMARK]
for ticker in SECTORS + [BENCHMARK]:
    if ticker not in _obv_available:
        obv_regime[ticker] = "N/D"
        continue
    try:
        cl = ohlcv_long["Close"][ticker].dropna()
        vo = ohlcv_long["Volume"][ticker].dropna()
        obv_regime[ticker] = obv_flow_regime(cl, vo) if len(cl) >= 60 else "N/D"
    except Exception:
        obv_regime[ticker] = "N/D"
df["Flow Regime"] = df.index.map(obv_regime)


# ========================
# UI TABS
# ========================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Dashboard Settoriale",
    "📈 Andamento Settoriale",
    "🔄 Rotazione Settoriale",
    "🫧 S&P 500 Bubble",
    "🇪🇺 Settoriali Eurostoxx 600",
    "🔁 Rotation Backtest",
    "🧪 Backtest RS",
])

# ========================
# TAB 1 — DASHBOARD
# ========================
with tab1:
    col1, col2 = st.columns([1.2, 1])
    with col1:
        colors = ['#FF6B6B','#4ECDC4','#45B7D1','#FFA07A','#98D8C8','#F7DC6F',
                  '#BB8FCE','#85C1E2','#F8B739','#52B788','#E76F51','#00FF00']
        tickers_list = ALL_TICKERS
        values       = [returns.loc[t, "1D"] for t in tickers_list]
        fig = go.Figure(data=[go.Bar(
            x=tickers_list, y=values,
            marker=dict(color=colors[:len(tickers_list)], line=dict(color='#333', width=1)),
            width=0.7, showlegend=False
        )])
        fig.update_layout(
            height=420, paper_bgcolor="#000", plot_bgcolor="#000",
            font=dict(color="white", size=12),
            title=dict(text="Variazione % Giornaliera", font=dict(size=16, color="#ff9900")),
            xaxis=dict(tickangle=0, gridcolor="#1a1a1a"),
            yaxis=dict(title="", gridcolor="#1a1a1a", zeroline=True, zerolinecolor="#444", zerolinewidth=2),
            margin=dict(l=40, r=20, t=50, b=40), bargap=0.15
        )
        st.plotly_chart(fig, width="stretch")
    with col2:
        for t, row in df.head(3).iterrows():
            badge    = vol_html[t]
            regime   = obv_regime.get(t, "N/D")
            reg_color= "#00ff55" if regime == "BULL FLOW" else "#ff4422" if regime == "BEAR FLOW" else "#888"
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

    st.markdown('<style>div[data-testid="stDataFrame"] { margin-top: -1rem; }</style>', unsafe_allow_html=True)

    def style_vol(val):
        v = str(val)
        if "ACCUMULO"   in v: return "background-color:#0d2b0d; color:#00ff55; font-weight:bold"
        if "DISTRIBUZ"  in v: return "background-color:#2b0d0d; color:#ff4422; font-weight:bold"
        if "ESAURIM"    in v: return "background-color:#2b1a00; color:#ffaa00; font-weight:bold"
        if "INVERSIONE" in v: return "background-color:#0d1a2b; color:#44aaff; font-weight:bold"
        if "INDECISO"   in v: return "background-color:#1a1a1a; color:#888888"
        return ""

    def style_flow_regime(val):
        if str(val) == "BULL FLOW": return "background-color:#0d2b0d; color:#00ff55; font-weight:bold"
        if str(val) == "BEAR FLOW": return "background-color:#2b0d0d; color:#ff4422; font-weight:bold"
        return "color:#888888"

    styled = df.round(2).style.map(style_vol, subset=["Vol Signal"]).map(style_flow_regime, subset=["Flow Regime"])
    st.dataframe(styled, width="stretch", column_config={
        "Vol Signal":  st.column_config.TextColumn("Vol Signal",  width="medium"),
        "Flow Regime": st.column_config.TextColumn("Flow Regime", width="small"),
    })

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

    st.markdown("""
    <div style="background:#0a0a0a;border:1px solid #1a1a1a;border-radius:8px;
                padding:10px 20px;margin-top:10px;font-size:0.82em;">
        <span style="color:#555;">Valutazione P/E settoriale: </span>
        <a href="https://worldperatio.com" target="_blank"
           style="color:#ff9900;text-decoration:none;font-weight:bold;">
           worldperatio.com</a>
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
    fig.add_trace(go.Scatter(x=norm.index, y=norm[BENCHMARK], name="SPY", line=dict(width=4, color="#00FF00")))
    fig.update_layout(paper_bgcolor="#000", plot_bgcolor="#000", font_color="white", yaxis_title="Variazione %")
    st.plotly_chart(fig, width="stretch")




# ========================
# TAB 3 — ROTAZIONE SETTORIALE v2
# ========================
with tab3:

    CYCLICALS  = ["XLK","XLY","XLF","XLI","XLE","XLB"]
    DEFENSIVES = ["XLP","XLV","XLU","XLRE"]

    # ── ROS v1 scalar
    rar_focus_v1      = rsr_df[["1M","3M","6M"]].mean(axis=1)
    rotation_score_v1 = rar_focus_v1.loc[CYCLICALS].mean() - rar_focus_v1.loc[DEFENSIVES].mean()

    # ── ROS v2 scalar (Intervento 1)
    rar_weighted_scalar = (
        rsr_df["1W"] * WEIGHTS_V2["1W"] + rsr_df["1M"] * WEIGHTS_V2["1M"] +
        rsr_df["3M"] * WEIGHTS_V2["3M"] + rsr_df["6M"] * WEIGHTS_V2["6M"]
    )
    rotation_score_v2_scalar = rar_weighted_scalar.loc[CYCLICALS].mean() - rar_weighted_scalar.loc[DEFENSIVES].mean()

    # ── Intervento 3 — Vol Confirmation
    vol_conf  = compute_vol_confirmation(vol_plain, CYCLICALS, DEFENSIVES)
    vol_mult  = compute_vol_multiplier(vol_conf)
    rotation_score_adjusted = rotation_score_v2_scalar * vol_mult

    # ── Serie storiche + Int.4 (anticipate per i box header)
    rotation_series_v1        = compute_rotation_score_series(prices).dropna()
    rotation_series_v2        = compute_rotation_score_series_v2(prices).dropna()
    adaptive_threshold_series = compute_adaptive_threshold(rotation_series_v2)
    _rs_std_v1    = float(rotation_series_v1.std()) if len(rotation_series_v1) > 5 else 5.0
    _threshold_v1 = round(_rs_std_v1 * 0.75, 2)
    _threshold_v2_now = float(adaptive_threshold_series.iloc[-1]) \
                        if not adaptive_threshold_series.empty else _threshold_v1
    band_deriv_series, band_stato = compute_band_derivative(adaptive_threshold_series, window=10)

    # ── Regime label
    if rotation_score_adjusted > 1.5:
        regime  = "🟢 ROTATION: RISK ON"
        bg      = "#003300"
        comment = "Ciclici dominanti — volume confermato" if vol_mult == 1.0 else "Ciclici dominanti — volume parziale"
    elif rotation_score_adjusted < -1.5:
        regime, bg, comment = "🔴 ROTATION: RISK OFF", "#330000", "Difensivi dominanti su timeframe medio"
    else:
        regime, bg, comment = "🟡 ROTATION: NEUTRAL", "#333300", "Equilibrio ciclici/difensivi"

    if   vol_conf >= 0.5:  vol_conf_label, vol_conf_color = "✅ VOLUME CONFERMA",    "#00ff55"
    elif vol_conf >= 0.0:  vol_conf_label, vol_conf_color = "⚠️ VOLUME PARZIALE",    "#ffaa00"
    else:                  vol_conf_label, vol_conf_color = "❌ VOLUME CONTRADDICE", "#ff4422"

    # ── Header: 4 box
    col_box1, col_box2, col_box3, col_box4 = st.columns(4)

    with col_box1:
        st.markdown(f"""
        <div style="background:{bg};padding:16px 24px;border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px;">ROS Adjusted</div>
            <div style="font-size:1.5em;font-weight:bold;">{regime}</div>
            <div style="font-size:1.0em;margin-top:4px;color:#aaa;">{rotation_score_adjusted:.2f}</div>
            <div style="font-size:0.78em;color:#666;margin-top:4px;">{comment}</div>
        </div>""", unsafe_allow_html=True)

    with col_box2:
        delta_v1_v2 = rotation_score_v2_scalar - rotation_score_v1
        delta_color = "#00ff55" if delta_v1_v2 >= 0 else "#ff4422"
        st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid #222;padding:16px 24px;border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">Confronto v1 → v2 → adj</div>
            <div style="font-size:0.88em;color:#aaa;">v1 (33/33/33): <b style="color:#dddddd">{rotation_score_v1:.2f}</b></div>
            <div style="font-size:0.88em;color:#aaa;margin-top:4px;">v2 (15/25/35/25): <b style="color:#dddddd">{rotation_score_v2_scalar:.2f}</b></div>
            <div style="font-size:0.88em;color:#aaa;margin-top:4px;">adjusted (×{vol_mult}): <b style="color:#ff9900">{rotation_score_adjusted:.2f}</b></div>
            <div style="font-size:0.80em;margin-top:6px;color:{delta_color};">Δ v1→v2: {delta_v1_v2:+.2f}</div>
        </div>""", unsafe_allow_html=True)

    with col_box3:
        st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid #222;padding:16px 24px;border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">Vol Confirmation</div>
            <div style="font-size:1.1em;font-weight:bold;color:{vol_conf_color};margin-top:4px;">{vol_conf_label}</div>
            <div style="font-size:0.88em;color:#aaa;margin-top:6px;">Score: <b style="color:{vol_conf_color}">{vol_conf:+.2f}</b> &nbsp;·&nbsp; Mult: <b style="color:#ff9900">×{vol_mult}</b></div>
            <div style="font-size:0.75em;color:#555;margin-top:6px;">Ciclici vol − Difensivi vol</div>
        </div>""", unsafe_allow_html=True)

    with col_box4:
        import math as _mh
        _bd_c = band_stato["color"]
        _bd_d = band_stato["deriv"]
        _bd_s = band_stato["deriv_std"]
        _bd_d_str = f"{_bd_d:+.2f}%" if not _mh.isnan(_bd_d) else "N/D"
        _bd_s_str = f"{_bd_s:.2f}"   if not _mh.isnan(_bd_s) else "N/D"
        st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid #222;padding:16px 24px;border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">Banda — Velocità</div>
            <div style="font-size:1.0em;font-weight:bold;color:{_bd_c};margin-top:4px;">{band_stato["stato"]}</div>
            <div style="font-size:0.85em;color:#aaa;margin-top:6px;">Δ banda 10gg: <b style="color:{_bd_c}">{_bd_d_str}</b></div>
            <div style="font-size:0.72em;color:#555;margin-top:4px;">σ derivata: {_bd_s_str}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # ── Timeframe selector
    tf_rot = st.radio("Storico grafico", ["1A","2A","3A","5A","Max"], index=0, horizontal=True, key="tf_rotation")
    _tf_rot_days = {"1A": 365, "2A": 730, "3A": 1095, "5A": 1825, "Max": 99999}

    def slice_series(s, days):
        if s.empty: return s
        return s[s.index >= s.index.max() - pd.Timedelta(days=days)]

    days_sel      = _tf_rot_days[tf_rot]
    plot_v1       = slice_series(rotation_series_v1, days_sel)
    plot_v2       = slice_series(rotation_series_v2, days_sel)
    plot_adaptive = slice_series(adaptive_threshold_series, days_sel)

    st.markdown(
        '<div style="color:#555;font-size:0.78em;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">'
        '◀ ROS v1 — pesi flat · soglia fissa &nbsp;|&nbsp; ROS v2 — pesi 15/25/35/25 · soglia adattiva · vol adjusted ▶'
        '</div>', unsafe_allow_html=True
    )

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig_v1 = go.Figure()
        fig_v1.add_trace(go.Scatter(x=plot_v1.index, y=plot_v1, mode="lines",
            line=dict(color="#888888", width=1.5), name="ROS v1", fill='tozeroy', fillcolor='rgba(100,100,100,0.12)'))
        fig_v1.add_hline(y=_threshold_v1,  line_dash="dot", line_color="#00AA00",
            annotation_text=f"Risk On +{_threshold_v1:.1f} (fissa)",  annotation_position="right",
            annotation_font=dict(size=9, color="#00AA00"))
        fig_v1.add_hline(y=0.0, line_dash="solid", line_color="#444444")
        fig_v1.add_hline(y=-_threshold_v1, line_dash="dot", line_color="#AA0000",
            annotation_text=f"Risk Off -{_threshold_v1:.1f} (fissa)", annotation_position="right",
            annotation_font=dict(size=9, color="#AA0000"))
        fig_v1.update_layout(height=300, margin=dict(l=40,r=90,t=30,b=40),
            paper_bgcolor="#000000", plot_bgcolor="#000000", font_color="white", showlegend=False,
            title=dict(text="ROS v1 — originale", font=dict(size=10, color="#666"), x=0, xanchor="left"),
            yaxis=dict(gridcolor="#1a1a1a", title=""), xaxis=dict(gridcolor="#1a1a1a"))
        st.plotly_chart(fig_v1, use_container_width=True)

    with col_g2:
        fig_v2 = go.Figure()
        if not plot_adaptive.empty and not plot_v2.empty:
            common_idx   = plot_v2.index.intersection(plot_adaptive.index)
            if len(common_idx) > 0:
                adap_aligned = plot_adaptive.reindex(common_idx).ffill()
                fig_v2.add_trace(go.Scatter(x=common_idx, y=adap_aligned, mode="lines",
                    line=dict(color="#00AA00", width=1, dash="dot"), showlegend=False, opacity=0.55))
                fig_v2.add_trace(go.Scatter(x=common_idx, y=-adap_aligned, mode="lines",
                    line=dict(color="#AA0000", width=1, dash="dot"),
                    fill='tonexty', fillcolor='rgba(80,80,80,0.07)', showlegend=False, opacity=0.55))
        fig_v2.add_trace(go.Scatter(x=plot_v2.index, y=plot_v2, mode="lines",
            line=dict(color="#DDDDDD", width=2), name="ROS v2", fill='tozeroy', fillcolor='rgba(120,120,120,0.13)'))
        if not plot_v2.empty:
            last_date = plot_v2.index[-1]
            adj_val   = float(plot_v2.iloc[-1]) * vol_mult
            mk_color  = "#00ff55" if vol_mult == 1.0 else "#ffaa00" if vol_mult == 0.75 else "#ff4422"
            fig_v2.add_trace(go.Scatter(x=[last_date], y=[adj_val], mode="markers",
                marker=dict(size=12, color=mk_color, symbol="diamond", line=dict(color="white", width=1.5)),
                hovertemplate=f"ROS adjusted: {adj_val:.2f}<extra></extra>"))
            fig_v2.add_annotation(x=last_date, y=_threshold_v2_now,
                text=f"+{_threshold_v2_now:.1f} adattiva", showarrow=False,
                font=dict(size=9, color="#00AA00"), xanchor="right", yanchor="bottom")
            fig_v2.add_annotation(x=last_date, y=-_threshold_v2_now,
                text=f"-{_threshold_v2_now:.1f} adattiva", showarrow=False,
                font=dict(size=9, color="#AA0000"), xanchor="right", yanchor="top")
        fig_v2.add_hline(y=0.0, line_dash="solid", line_color="#444444")
        fig_v2.update_layout(height=300, margin=dict(l=40,r=90,t=30,b=40),
            paper_bgcolor="#000000", plot_bgcolor="#000000", font_color="white", showlegend=False,
            title=dict(text=f"ROS v2 — adjusted · ◆ = punto corrente ×{vol_mult}",
                        font=dict(size=10, color="#666"), x=0, xanchor="left"),
            yaxis=dict(gridcolor="#1a1a1a", title=""), xaxis=dict(gridcolor="#1a1a1a"))
        st.plotly_chart(fig_v2, use_container_width=True)

    # ── Int.4 — grafico derivata banda
    if not band_deriv_series.empty:
        plot_deriv = slice_series(band_deriv_series, days_sel)
        if not plot_deriv.empty:
            import math as _m4
            _s_str, _s_lar = band_stato["soglia_stretta"], band_stato["soglia_larga"]
            _s_ok, _l_ok   = not _m4.isnan(_s_str), not _m4.isnan(_s_lar)
            bar_colors_d = []
            for _v in plot_deriv:
                if _s_ok and _v < _s_str * 2:   bar_colors_d.append("#ff4422")
                elif _s_ok and _v < _s_str:      bar_colors_d.append("#ffaa00")
                elif _l_ok and _v > _s_lar * 2:  bar_colors_d.append("#44aaff")
                elif _v > 0:                      bar_colors_d.append("#555555")
                else:                             bar_colors_d.append("#333333")
            fig_d4 = go.Figure()
            fig_d4.add_trace(go.Bar(x=plot_deriv.index, y=plot_deriv, marker_color=bar_colors_d,
                hovertemplate="Delta banda: %{y:+.2f}%<extra></extra>"))
            fig_d4.add_hline(y=0, line_color="#555", line_width=1)
            if _s_ok:
                fig_d4.add_hline(y=_s_str, line_dash="dot", line_color="#ffaa00",
                    annotation_text="stretta", annotation_font=dict(size=8, color="#ffaa00"), annotation_position="right")
                fig_d4.add_hline(y=_s_str*2, line_dash="dot", line_color="#ff4422",
                    annotation_text="stretta rapida", annotation_font=dict(size=8, color="#ff4422"), annotation_position="right")
            if _l_ok:
                fig_d4.add_hline(y=_s_lar*2, line_dash="dot", line_color="#44aaff",
                    annotation_text="larga rapida", annotation_font=dict(size=8, color="#44aaff"), annotation_position="right")
            fig_d4.update_layout(height=155, margin=dict(l=40,r=110,t=22,b=30),
                paper_bgcolor="#000", plot_bgcolor="#000", font_color="white", showlegend=False,
                title=dict(text="Int.4 — Velocita banda adattiva (10gg)  |  rosso=stringe [pericolo] · grigio=stabile · blu=allarga [ritardo segnale]",
                            font=dict(size=9, color="#555"), x=0, xanchor="left"),
                yaxis=dict(gridcolor="#1a1a1a", ticksuffix="%", title=""),
                xaxis=dict(gridcolor="#1a1a1a"))
            st.plotly_chart(fig_d4, use_container_width=True)

    # ── Legenda interventi
    _bd_leg_str = f"{band_stato['stato']} ({band_stato['deriv']:+.2f}%)"
    st.markdown(f"""
    <div style="background:#080808;border:1px solid #1a1a1a;border-radius:8px;
                padding:12px 20px;margin-top:2px;font-size:0.80em;color:#666;display:flex;gap:28px;flex-wrap:wrap;">
        <span><b style="color:#ff9900">Int.1</b> — peso 1W=15% leading edge · pesi 15·25·35·25</span>
        <span><b style="color:#ff9900">Int.2</b> — soglia adattiva rolling(252)×0.75 · ora: ±{_threshold_v2_now:.2f} vs fissa ±{_threshold_v1:.2f}</span>
        <span><b style="color:#ff9900">Int.3</b> — vol mult ×{vol_mult} (score {vol_conf:+.2f}) · <span style="color:{vol_conf_color}">{vol_conf_label}</span></span>
        <span><b style="color:#ff9900">Int.4</b> — banda: <span style="color:{band_stato['color']}">{_bd_leg_str}</span></span>
    </div>""", unsafe_allow_html=True)

    # ── Expander: Vol Confirmation dettaglio
    with st.expander("🔬 Dettaglio Vol Confirmation per settore", expanded=False):
        vol_detail_rows = [{"Ticker": t, "Tipo": "Ciclico" if t in CYCLICALS else "Difensivo",
                             "Vol Signal": vol_plain.get(t, "[B~ M~] INDECISO"),
                             "Score": VOL_SCORE_MAP.get(vol_plain.get(t, "[B~ M~] INDECISO"), 0.0)}
                           for t in CYCLICALS + DEFENSIVES]
        vd_df = pd.DataFrame(vol_detail_rows)
        def style_vol_score(val):
            if val > 0.5:  return "color:#00ff55;font-weight:bold"
            if val > 0:    return "color:#88cc88"
            if val < -0.5: return "color:#ff4422;font-weight:bold"
            if val < 0:    return "color:#cc6644"
            return "color:#666"
        def style_tipo(val):
            return "color:#ffaa00" if val == "Ciclico" else "color:#44aaff"
        st.dataframe(vd_df.style.map(style_vol_score, subset=["Score"]).map(style_tipo, subset=["Tipo"]),
                     use_container_width=True, hide_index=True)
        cyc_avg = np.mean([VOL_SCORE_MAP.get(vol_plain.get(t,"[B~ M~] INDECISO"),0.0) for t in CYCLICALS])
        def_avg = np.mean([VOL_SCORE_MAP.get(vol_plain.get(t,"[B~ M~] INDECISO"),0.0) for t in DEFENSIVES])
        st.markdown(
            f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:6px;padding:8px 16px;'
            f'margin-top:6px;font-size:0.82em;color:#888;display:flex;gap:28px;flex-wrap:wrap;">'
            f'<span>Media ciclici: <b style="color:#ffaa00">{cyc_avg:+.2f}</b></span>'
            f'<span>Media difensivi: <b style="color:#44aaff">{def_avg:+.2f}</b></span>'
            f'<span>Vol confirmation: <b style="color:{vol_conf_color}">{vol_conf:+.2f}</b></span>'
            f'<span>Multiplier: <b style="color:#ff9900">×{vol_mult}</b></span></div>',
            unsafe_allow_html=True)

    # ── Expander: Episodi Risk Off
    with st.expander("🔬 Episodi Risk Off — analisi storica", expanded=False):
        confirm_sel = st.radio("Giorni conferma anti-whipsaw", [2,3,5], index=1, horizontal=True,
                               key="rs_confirm_days")
        episodes = compute_risk_off_episodes(rotation_series_v2, _threshold_v2_now, confirm_days=confirm_sel)
        if not episodes:
            st.info("Nessun episodio Risk Off identificato con i parametri correnti.")
        else:
            st.markdown(
                f'<div style="color:#555;font-size:0.78em;margin-bottom:8px;">'
                f'Soglia adattiva corrente: RS &lt; <b style="color:#AA0000">-{_threshold_v2_now:.1f}</b> · '
                f'Conferma: <b>{confirm_sel}</b> giorni · Episodi: <b style="color:#ff9900">{len(episodes)}</b></div>',
                unsafe_allow_html=True)
            rows_ep = []
            for i, ep in enumerate(episodes, 1):
                stato   = "🔴 APERTO" if ep["open"] else "✅ chiuso"
                end_str = "in corso"  if ep["open"] else ep["end"].strftime("%d/%m/%Y")
                rows_ep.append({"#": i, "Inizio": ep["start"].strftime("%d/%m/%Y"),
                                 "Confermato": ep["confirmed"].strftime("%d/%m/%Y"),
                                 "Fine": end_str, "Durata (gg)": ep["duration"],
                                 "RS minimo": ep["rs_min"],
                                 "Data minimo": ep["rs_min_date"].strftime("%d/%m/%Y"), "Stato": stato})
            ep_df = pd.DataFrame(rows_ep)
            def style_ep(row):
                if "APERTO" in str(row["Stato"]): return ["background-color:#1a0000; color:#ff4422"] * len(row)
                return ["color:#aaaaaa"] * len(row)
            def style_rs_min(val):
                try:
                    v = float(val)
                    if v < -7: return "color:#ff4422;font-weight:bold"
                    if v < -5: return "color:#ffaa00;font-weight:bold"
                    return "color:#888888"
                except Exception: return ""
            st.dataframe(ep_df.style.apply(style_ep, axis=1).map(style_rs_min, subset=["RS minimo"]),
                         use_container_width=True, hide_index=True,
                         column_config={"Durata (gg)": st.column_config.NumberColumn(format="%d"),
                                        "RS minimo":   st.column_config.NumberColumn(format="%.2f")})
            closed = [e for e in episodes if not e["open"]]
            if closed:
                durate, minimi = [e["duration"] for e in closed], [e["rs_min"] for e in closed]
                st.markdown(
                    f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;'
                    f'padding:10px 20px;margin-top:8px;font-size:0.82em;color:#888;display:flex;gap:28px;flex-wrap:wrap;">'
                    f'<span>Episodi chiusi: <b style="color:#ff9900">{len(closed)}</b></span>'
                    f'<span>Durata media: <b style="color:#ff9900">{int(sum(durate)/len(durate))} gg</b></span>'
                    f'<span>Durata max: <b style="color:#ff9900">{max(durate)} gg</b></span>'
                    f'<span>RS minimo storico: <b style="color:#ff4422">{min(minimi):.2f}</b></span>'
                    f'<span>RS minimo medio: <b style="color:#ffaa00">{sum(minimi)/len(minimi):.2f}</b></span></div>',
                    unsafe_allow_html=True)

    # ── Cross-asset OBV Flow Chart
    st.markdown("---")
    st.markdown(
        '<h4 style="color:#ff9900;margin-bottom:2px;">📊 Cross-Asset OBV Flow</h4>'
        '<p style="color:#555;font-size:0.80em;margin-top:0;">'
        'flowEMA normalizzata su scala comune — confronto volumetrico cross-settoriale impossibile in TradingView</p>',
        unsafe_allow_html=True)

    col_obv1, col_obv2, col_obv3 = st.columns([3, 1, 1])
    with col_obv1:
        obv_tickers_sel = st.multiselect("Strumenti da confrontare", options=SECTORS + [BENCHMARK],
                                          default=["XLK","XLY","XLF","XLV","SPY"], key="obv_cross_sel")
    with col_obv2:
        obv_tf = st.radio("Finestra chart", ["6M","1A","2A","Max"], index=1, horizontal=False, key="obv_tf_sel")
    with col_obv3:
        show_trend_filter = st.checkbox("Mostra Trend Filter", value=False, key="obv_show_trend")

    _obv_tf_days = {"6M": 126, "1A": 252, "2A": 504, "Max": 99999}

    if obv_tickers_sel:
        obv_palette = ["#ff9900","#00ff55","#44aaff","#ff4422","#ffff44",
                       "#bb44ff","#00ffcc","#ff66cc","#88cc88","#cc8844","#4488ff","#ff8844"]
        fig_obv  = go.Figure()
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
                days_obv = _obv_tf_days[obv_tf]
                if days_obv < 99999:
                    cutoff = fe.index.max() - pd.Timedelta(days=days_obv)
                    fe = fe[fe.index >= cutoff]
                    ft = ft[ft.index >= cutoff]
                color   = obv_palette[i % len(obv_palette)]
                fe_mean, fe_std = fe.mean(), fe.std()
                if fe_std == 0 or np.isnan(fe_std):
                    continue
                fe_norm = (fe - fe_mean) / fe_std
                ft_norm = (ft - fe_mean) / fe_std
                fig_obv.add_trace(go.Scatter(x=fe_norm.index, y=fe_norm, mode="lines", name=ticker,
                    line=dict(color=color, width=2),
                    hovertemplate=f"<b>{ticker}</b><br>%{{x|%d %b %Y}}<br>Flow (z): %{{y:.2f}}<extra></extra>"))
                if show_trend_filter and not ft_norm.empty:
                    fig_obv.add_trace(go.Scatter(x=ft_norm.index, y=ft_norm, mode="lines",
                        name=f"{ticker} trend", line=dict(color=color, width=1, dash="dot"),
                        opacity=0.45, showlegend=False,
                        hovertemplate=f"<b>{ticker} trend</b><br>%{{x|%d %b %Y}}<br>%{{y:.2f}}<extra></extra>"))
                obv_loaded += 1
            except Exception:
                continue

        if obv_loaded == 0:
            st.warning("Dati OBV non disponibili per i ticker selezionati.")
        else:
            fig_obv.add_hline(y=0, line_color="#444", line_width=1, line_dash="dot")
            fig_obv.update_layout(height=380, paper_bgcolor="#000000", plot_bgcolor="#000000",
                font=dict(color="white", size=10),
                title=dict(text="OBV Flow EMA — normalizzata z-score (scala comune)  |  sopra 0 = accumulo strutturale relativo",
                            font=dict(size=9, color="#555"), x=0, xanchor="left"),
                xaxis=dict(gridcolor="#1a1a1a"),
                yaxis=dict(gridcolor="#1a1a1a", title="Flow z-score", zeroline=False),
                legend=dict(font=dict(size=9), bgcolor="rgba(0,0,0,0.6)", bordercolor="#333", borderwidth=1,
                            orientation="h", y=1.04, x=0, xanchor="left"),
                margin=dict(l=50, r=30, t=45, b=40), hovermode="x unified")
            st.plotly_chart(fig_obv, use_container_width=True)

            regime_rows = [{"Ticker": ticker, "Flow Regime": obv_regime.get(ticker, "N/D"),
                             "RSR 1M": round(float(rsr_df.loc[ticker, "1M"]), 2) if ticker in rsr_df.index else np.nan,
                             "Vol Signal": vol_plain.get(ticker, "—")} for ticker in obv_tickers_sel]
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
            st.dataframe(reg_df.style.map(_style_regime, subset=["Flow Regime"]).map(_style_vol_plain, subset=["Vol Signal"]),
                         use_container_width=True, hide_index=True,
                         column_config={"Flow Regime": st.column_config.TextColumn("Flow Regime", width="small"),
                                        "Vol Signal":  st.column_config.TextColumn("Vol Signal",  width="medium"),
                                        "RSR 1M":      st.column_config.NumberColumn("RSR 1M", format="%.2f")})

    st.markdown(
        '<div style="background:#080808;border:1px solid #1a1a1a;border-radius:6px;'
        'padding:8px 16px;margin-top:6px;font-size:0.78em;color:#555;">'
        '<b style="color:#ff9900">Flow Regime</b>: flowEMA &gt; flowTrend → BULL · flowEMA &lt; flowTrend → BEAR &nbsp;|&nbsp; '
        '<b style="color:#ff9900">Scala</b>: z-score per confronto cross-asset (parametri Daily: vol=20 · ema=13 · trend=50)'
        '</div>', unsafe_allow_html=True)

    # ── Spiegazione
    st.markdown(f"""
    <div style="background:#0d0d0d;padding:25px;border-radius:10px;font-size:1.0em;line-height:1.7;margin-top:8px;">
    <h3 style="color:#ff9900;margin-top:0;">📊 ROS 2.0 — Quattro Interventi</h3>
    <b style="color:#ff9900">Intervento 1 — Leading Edge 1W</b><br>
    Peso 1W=15% per catturare rotazioni emergenti prima che si consolidino nel mensile.
    Pesi: 1W=15% · 1M=25% · 3M=35% · 6M=25%.<br><br>
    <b style="color:#ff9900">Intervento 2 — Soglia Adattiva</b><br>
    Rolling std 252gg × 0.75. In laterale si restringe (meno falsi segnali), in trend si allarga.
    Corrente: <b style="color:#ff9900">±{_threshold_v2_now:.2f}</b> vs fissa v1: <b style="color:#888">±{_threshold_v1:.2f}</b><br><br>
    <b style="color:#ff9900">Intervento 3 — Vol Confirmation</b><br>
    VWDS settoriali aggregati in Vol Confirmation Score ({vol_conf:+.2f}).
    Stato: <b style="color:{vol_conf_color}">{vol_conf_label}</b> → ×{vol_mult}<br><br>
    <b style="color:#ff9900">Intervento 4 — Derivata Banda</b><br>
    Velocità di variazione della soglia adattiva. Rosso = banda stringe (soglia si avvicina al ROS).
    Stato: <b style="color:{band_stato['color']}">{band_stato['stato']}</b> ({band_stato['deriv']:+.2f}%)
    <h3 style="color:#ff9900;margin-top:20px;">🎯 Situazione Attuale</h3>
    <div style="background:#1a1a1a;padding:15px;border-radius:8px;">
        ROS v1: <b>{rotation_score_v1:.2f}</b> → ROS v2: <b>{rotation_score_v2_scalar:.2f}</b> →
        ROS adjusted: <b style="color:#ff9900">{rotation_score_adjusted:.2f}</b> · {comment}
    </div></div>""", unsafe_allow_html=True)


# ========================
# TAB 4 — BUBBLE CHART S&P 500
# ========================
with tab4:
    tf_options = {"1W": 5, "1M": 21, "3M": 63, "6M": 126,
                  "YTD": (datetime.today() - datetime(datetime.today().year, 1, 1)).days}
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
                "Totale": len(g), "Positive": (g["Return"] > 0).sum(),
                "Negative": (g["Return"] <= 0).sum(),
                "Pct_pos": round((g["Return"] > 0).mean() * 100, 1),
                "Avg_ret": round(g["Return"].mean(), 2),
            }), include_groups=False)
            .reset_index().sort_values("Pct_pos", ascending=False)
        )
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name="% Positive", x=sector_stats["Sector"], y=sector_stats["Pct_pos"],
            marker_color="#00cc44", text=sector_stats["Pct_pos"].astype(str) + "%",
            textposition="outside", textfont=dict(size=10, color="#00cc44")))
        fig_bar.add_hline(y=50, line_dash="dot", line_color="#555555",
                          annotation_text="50%", annotation_font_color="#888", annotation_position="right")
        fig_bar.update_layout(height=220, paper_bgcolor="#000", plot_bgcolor="#000",
            font=dict(color="white", size=11),
            title=dict(text=f"% Titoli Positivi per Settore — {tf_sel}", font=dict(size=13, color="#ff9900")),
            xaxis=dict(tickangle=-30, gridcolor="#111"),
            yaxis=dict(range=[0, 115], gridcolor="#111", ticksuffix="%"),
            margin=dict(l=40, r=20, t=45, b=80), showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

        tot    = len(sp500_df)
        pos    = (sp500_df["Return"] > 0).sum()
        pct    = round(pos / tot * 100, 1)
        colore = "#00ff55" if pct >= 50 else "#ff4422"
        st.markdown(
            f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;'
            f'padding:10px 20px;margin-bottom:10px;font-size:1.05em;">'
            f'📊 Su timeframe <b>{tf_sel}</b>: <b style="color:{colore}">{pos} titoli su {tot} ({pct}%)</b> '
            f'sono in territorio positivo nell\'S&P 500</div>', unsafe_allow_html=True)

        sector_order         = sector_stats["Sector"].tolist()
        sp500_df["SectorRank"]= sp500_df["Sector"].map({s: i for i, s in enumerate(sector_order)})
        sp500_df             = sp500_df.sort_values("SectorRank")
        colors_b             = sp500_df["Return"].apply(lambda r: "#00cc44" if r > 0 else "#ff3322")
        np.random.seed(42)
        jitter = np.random.uniform(-0.35, 0.35, size=len(sp500_df))
        x_vals = sp500_df["SectorRank"] + jitter
        fig_bubble = go.Figure()
        fig_bubble.add_hline(y=0, line_color="#444444", line_width=1.5)
        fig_bubble.add_trace(go.Scatter(x=x_vals, y=sp500_df["Return"], mode="markers",
            marker=dict(size=5, color=colors_b, opacity=0.75, line=dict(width=0)),
            text=sp500_df["Ticker"] + "<br>" + sp500_df["Return"].astype(str) + "%",
            hovertemplate="%{text}<extra></extra>", showlegend=False))
        tick_labels = []
        for _, row in sector_stats.iterrows():
            short = row["Sector"].replace(" & ", "/").replace(" ", "<br>")
            tick_labels.append(f"{short}<br><span style='color:#00cc44'>{int(row['Positive'])}↑</span> "
                                f"<span style='color:#ff3322'>{int(row['Negative'])}↓</span>")
        fig_bubble.update_layout(height=520, paper_bgcolor="#000000", plot_bgcolor="#000000",
            font=dict(color="white", size=10),
            title=dict(text=f"S&P 500 — Ritorno {tf_sel} per Titolo e Settore", font=dict(size=14, color="#ff9900")),
            xaxis=dict(tickmode="array", tickvals=list(range(len(sector_order))), ticktext=tick_labels,
                       tickangle=0, gridcolor="#111111", showline=False),
            yaxis=dict(title="Ritorno %", gridcolor="#1a1a1a", zeroline=False, ticksuffix="%"),
            margin=dict(l=60, r=20, t=50, b=120), hoverlabel=dict(bgcolor="#111", font_size=12))
        st.plotly_chart(fig_bubble, use_container_width=True)

        with st.expander("📋 Tabella dettaglio settori", expanded=False):
            display_stats = sector_stats[["Sector","Totale","Positive","Negative","Pct_pos","Avg_ret"]].copy()
            display_stats.columns = ["Settore","Totale","Positive ↑","Negative ↓","% Positive","Ritorno Medio %"]
            def style_pct(val):
                if val >= 60: return "color:#00ff55; font-weight:bold"
                if val <= 40: return "color:#ff4422; font-weight:bold"
                return "color:#ffff44"
            st.dataframe(display_stats.style.map(style_pct, subset=["% Positive"]),
                         use_container_width=True, hide_index=True)





# ========================
# TAB 5 — SETTORIALI EUROSTOXX 600
# ========================
with tab5:
    st.markdown(
        '<h3 style="color:#ff9900;margin-bottom:2px;">🇪🇺 Settoriali STOXX Europe 600</h3>'
        '<p style="color:#555;font-size:0.82em;margin-top:0;">'
        '19 ETF iShares · Benchmark EXSA.DE · RSr gaussiano · Gate sequenziale MMS6M→TT→Mr Index→MBI</p>',
        unsafe_allow_html=True)

    with st.spinner("Caricamento prezzi Eurostoxx..."):
        euro_prices       = load_euro_prices()
        euro_prices_today = load_euro_prices_today()

    available_euro = [t for t in EURO_ALL if t in euro_prices.columns]
    missing_euro   = [t for t in EURO_ALL if t not in euro_prices.columns]
    if missing_euro:
        st.warning(f"Ticker non trovati: {', '.join(missing_euro)}")
    if EURO_BENCHMARK not in euro_prices.columns:
        st.error(f"Benchmark {EURO_BENCHMARK} non disponibile.")
        st.stop()

    euro_prices_clean = euro_prices[available_euro].copy()
    euro_today_avail  = [t for t in available_euro if t in euro_prices_today.columns]
    euro_today_clean  = euro_prices_today[euro_today_avail].copy()

    with st.spinner("Calcolo indicatori RSr..."):
        euro_ind = compute_euro_indicators(euro_prices_clean, euro_today_clean, EURO_BENCHMARK)

    
    # ── Controlli UI
    c1, c2 = st.columns([2, 2])
    with c1:
        euro_tf   = st.selectbox("Timeframe grafico",
            ["1D","1W","1M","3M","6M","YTD","1A"], index=4, key="euro_tf")
    with c2:
        euro_sort = st.selectbox("Ordina tabella per",
            ["MMS6M RSr","MMS6M Ass.","Tact. Thrust","Mr Index","RSr 1M","RSr 3M"],
            key="euro_sort")

    # ── 1. BAR CHART RSr
    tf_days_map = {"1D":1,"1W":5,"1M":21,"3M":63,"6M":126,"YTD":None,"1A":252}
    bar_data = []
    for tk in EURO_SECTORS:
        if tk not in euro_prices_clean.columns: continue
        d = tf_days_map[euro_tf]
        if d == 1:
            s = euro_today_clean[tk].dropna() if tk in euro_today_clean.columns else pd.Series(dtype=float)
            b = euro_today_clean[EURO_BENCHMARK].dropna() if EURO_BENCHMARK in euro_today_clean.columns else pd.Series(dtype=float)
        else:
            s = euro_prices_clean[tk].dropna()
            b = euro_prices_clean[EURO_BENCHMARK].dropna()
        rs = safe_ret(s, d); rb = safe_ret(b, d)
        if not np.isnan(rs) and not np.isnan(rb):
            rsr_val = float((1+rs/100)/(1+rb/100)-1)
        else:
            rsr_val = np.nan
        bar_data.append({"Ticker":tk, "Nome":EURO_NAMES.get(tk,tk), "RSr":rsr_val})

    bar_df = pd.DataFrame(bar_data).dropna(subset=["RSr"]).sort_values("RSr", ascending=True)
    bar_colors = ["#00cc44" if v>=0 else "#cc2200" for v in bar_df["RSr"]]
    fig_bar = go.Figure(go.Bar(
        x=bar_df["RSr"]*100, y=bar_df["Nome"], orientation="h",
        marker=dict(color=bar_colors, line=dict(color="#333",width=1)),
        text=[f"{v*100:+.2f}%" for v in bar_df["RSr"]],
        textposition="outside", textfont=dict(color="white",size=9),
    ))
    fig_bar.add_vline(x=0, line_color="#444", line_width=1.5)
    fig_bar.update_layout(
        height=520, paper_bgcolor="#000", plot_bgcolor="#000",
        font=dict(color="white",size=9),
        title=dict(text=f"RSr vs EXSA — {euro_tf}  |  Forza relativa settoriale",
                   font=dict(size=10,color="#ff9900")),
        xaxis=dict(gridcolor="#1a1a1a", ticksuffix="%", zeroline=False),
        yaxis=dict(gridcolor="#0a0a0a"),
        margin=dict(l=130,r=80,t=40,b=30),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── 2. SCATTER QUADRANTI
    st.markdown("---")
    sc_c1, sc_c2 = st.columns([3,1])
    with sc_c1:
        st.markdown("#### Scatter — RSr 1M vs RSr 3M")
    with sc_c2:
        sc_lbl = st.radio("Etichette", ["Ticker","Nome"], horizontal=True, key="euro_sc_lbl")

    sc_data = []
    for tk in EURO_SECTORS:
        if tk not in euro_ind.index: continue
        sc_data.append({
            "Ticker": tk, "Nome": EURO_NAMES.get(tk,tk),
            "RSr 1M": euro_ind.loc[tk,"RSr 1M"],
            "RSr 3M": euro_ind.loc[tk,"RSr 3M"],
        })
    sc_df = pd.DataFrame(sc_data).dropna(subset=["RSr 1M","RSr 3M"])

    if not sc_df.empty:
        def _gte_color(v):
            if pd.isna(v): return "#888888"
            return "#00cc44" if v > 0 else "#cc2200"
        sc_df["_color"] = sc_df["GTE"].apply(_gte_color)

        fig_sc = go.Figure()
        lbl = sc_df["Ticker"] if sc_lbl=="Ticker" else sc_df["Nome"]
        fig_sc.add_trace(go.Scatter(
            x=sc_df["RSr 1M"]*100, y=sc_df["RSr 3M"]*100,
            mode="markers+text",
            name="Settori",
            marker=dict(size=11, color=sc_df["_color"],
                        opacity=0.85, line=dict(color="#111",width=1)),
            text=lbl, textposition="top center",
            textfont=dict(size=8,color="#ccc"),
            hovertemplate="<b>%{text}</b><br>RSr 1M: %{x:.2f}%<br>RSr 3M: %{y:.2f}%<extra></extra>",
        ))

        fig_sc.add_hline(y=0, line_color="#333", line_width=1.5)
        fig_sc.add_vline(x=0, line_color="#333", line_width=1.5)
        x_rng = sc_df["RSr 1M"].max()*100
        y_rng = sc_df["RSr 3M"].max()*100
        for qx,qy,ql,qc,qax,qay in [
            ( x_rng*0.85,  y_rng*0.85, "LEADER",    "#00ff55","right","top"),
            (-x_rng*0.85,  y_rng*0.85, "IMPROVING", "#44aaff","left", "top"),
            ( x_rng*0.85, -y_rng*0.85, "WEAKENING", "#ffaa00","right","bottom"),
            (-x_rng*0.85, -y_rng*0.85, "LAGGARD",   "#ff4422","left", "bottom"),
        ]:
            fig_sc.add_annotation(x=qx, y=qy, text=ql, showarrow=False,
                font=dict(color=qc,size=10,family="Courier New"),
                opacity=0.45, xanchor=qax, yanchor=qay)
        fig_sc.update_layout(
            height=460, paper_bgcolor="#000", plot_bgcolor="#000",
            font=dict(color="white",size=10),
            title=dict(text="Scatter RSr 1M (X) vs RSr 3M (Y) — colore: GTE positivo=verde / negativo=rosso",
                       font=dict(size=10,color="#666")),
            xaxis=dict(title="RSr 1M (%)",gridcolor="#1a1a1a",ticksuffix="%",zeroline=False),
            yaxis=dict(title="RSr 3M (%)",gridcolor="#1a1a1a",ticksuffix="%",zeroline=False),
            legend=dict(font=dict(size=9),bgcolor="rgba(0,0,0,0.5)",
                        bordercolor="#333",borderwidth=1),
            margin=dict(l=60,r=40,t=50,b=60),
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    # ── 3. TABELLA INDICATORI
    st.markdown("---")
    st.markdown("#### Tabella indicatori — formattazione condizionale")

    disp = euro_ind.sort_values(euro_sort, ascending=False).copy()
    disp_show = disp[["Nome","RSr 1D","RSr 1W","RSr 1M","RSr 3M","RSr 6M",
                       "MMS6M RSr","MMS6M Ass.","Tact. Thrust","Mr Index","MBI"]].copy()

    def _c_rsr(v):
        try:
            v=float(v)
            if v>0.02:  return "color:#00ff55"
            if v>0:     return "color:#88cc88"
            if v<-0.02: return "color:#ff4422"
            if v<0:     return "color:#cc6644"
        except: pass
        return "color:#888"

    def _c_mms_rsr(v):
        try:
            v=float(v)
            if v>0.01:  return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
            if v<-0.01: return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
        except: pass
        return "color:#888"

    def _c_mms_abs(v):
        try:
            v=float(v)
            if v>0.03:  return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
            if v<-0.03: return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
        except: pass
        return "color:#888"

    def _c_tt(v):
        try:
            v=float(v)
            if v>0.015:  return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
            if v<-0.015: return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
        except: pass
        return "color:#888"

    def _c_mr(v):
        try:
            v=float(v)
            if v>0.01:   return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
            if v>0.005:  return "color:#88cc88"
            if v<-0.01:  return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
            if v<-0.005: return "color:#cc6644"
        except: pass
        return "color:#888"

    def _c_mbi(v):
        try:
            v=float(v)
            if v<-1.00:  return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
            if v<-0.50:  return "color:#aaff44"
            if v>1.00:   return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
            if v>0.50:   return "color:#ffaa00"
        except: pass
        return "color:#888"

    def _c_seg(v):
        if "ATTIVO"    in str(v): return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
        if "FILTRATO"  in str(v): return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
        if "WATCHLIST" in str(v): return "background-color:#2b2200;color:#ffaa00;font-weight:bold"
        return ""

    fp = lambda x: f"{x*100:+.2f}%" if not pd.isna(x) else "—"
    fm = lambda x: f"{x:+.2f}"      if not pd.isna(x) else "—"

    def _c_gemini(v):
        try:
            v=float(v)
            if v>0.005:  return "color:#00ff55"
            if v>0:      return "color:#88cc88"
            if v<-0.005: return "color:#ff4422"
            if v<0:      return "color:#cc6644"
        except: pass
        return "color:#888"

    def _c_gte(v):
        try:
            v=float(v)
            if v>1.0:   return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
            if v>0.3:   return "color:#88cc88"
            if v>0:     return "color:#aaaaaa"
            if v<-1.0:  return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
            if v<0:     return "color:#cc6644"
        except: pass
        return "color:#888"

    st.dataframe(
        disp_show.style
        .map(_c_rsr,     subset=["RSr 1D","RSr 1W","RSr 1M","RSr 3M","RSr 6M"])
        .map(_c_mms_rsr, subset=["MMS6M RSr"])
        .map(_c_mms_abs, subset=["MMS6M Ass."])
        .map(_c_tt,      subset=["Tact. Thrust"])
        .map(_c_mr,      subset=["Mr Index"])
        .map(_c_mbi,     subset=["MBI"])
        .format({"RSr 1D":fp,"RSr 1W":fp,"RSr 1M":fp,"RSr 3M":fp,"RSr 6M":fp,
                 "MMS6M RSr":fp,"MMS6M Ass.":fp,"Tact. Thrust":fp,"Mr Index":fp,"MBI":fm}),
        use_container_width=True,
        column_config={
            "Nome": st.column_config.TextColumn("Settore", width="medium"),
        }
    )
    st.markdown("""
    <div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;
                padding:12px 20px;margin-top:8px;font-size:0.80em;color:#888;
                display:flex;gap:20px;flex-wrap:wrap;">
        <span><b style="color:#ff9900">MMS6M RSr</b>: pesi 1W×20% 1M×35% 3M×25% 6M×20%</span>
        <span><b style="color:#ff9900">Tact.Thrust</b>: breve − medio (accelerazione)</span>
        <span><b style="color:#ff9900">Mr Index</b>: breve / (|medio|+0.02)</span>
        <span><b style="color:#ff9900">MBI</b>: attivo solo se MMS6M RSr &gt; 3%</span>
    </div>
    """, unsafe_allow_html=True)
# ========================
# TAB 6 — ROTATION BACKTEST
# ========================
with tab6:
    st.markdown(
        '<h3 style="color:#ff9900;margin-bottom:2px;">🔁 Rotation Backtest</h3>'
        '<p style="color:#555;font-size:0.82em;margin-top:0;">'
        'Strumento universale — Eurostoxx precaricato · ticker e benchmark modificabili · '
        'calcola indicatori e rendimenti forward a una data storica</p>',
        unsafe_allow_html=True)

    col_tk, col_bm = st.columns([3, 1])
    with col_tk:
        bt_tickers_raw = st.text_area(
            "Ticker (uno per riga)",
            value="\n".join(EURO_SECTORS),
            height=220, key="bt_tickers")
    with col_bm:
        bt_benchmark = st.text_input("Benchmark", value=EURO_BENCHMARK, key="bt_bm").strip().upper()
        bt_ref_date  = st.date_input(
            "Data di riferimento",
            value=datetime.today().date() - timedelta(days=90),
            min_value=datetime(2010,1,1).date(),
            max_value=datetime.today().date(),
            key="bt_date")

    st.markdown("##### Parametri")
    with st.columns([1,3])[0]:
        bt_thr_mbi = st.slider("MBI alert", 0.50,1.50,1.00,0.10, format="%.2f",key="bt_mbi")

    st.markdown("##### Rendimenti forward")
    fw1, fw2 = st.columns(2)
    with fw1: bt_fw1 = st.selectbox("TF forward 1", ["1M","3M","6M"], index=1, key="bt_fw1")
    with fw2: bt_fw2 = st.selectbox("TF forward 2", ["3M","6M","1A"], index=1, key="bt_fw2")
    fw_days_map = {"1M":21,"3M":63,"6M":126,"1A":252}

    if st.button("Calcola Backtest", type="primary", key="bt_run"):
        bt_tickers = [t.strip().upper() for t in bt_tickers_raw.strip().splitlines() if t.strip()]
        if not bt_tickers:
            st.error("Inserisci almeno un ticker.")
            st.stop()

        bt_all  = bt_tickers + [bt_benchmark]
        ref_dt  = pd.Timestamp(bt_ref_date)
        fwd1_d  = fw_days_map[bt_fw1]
        fwd2_d  = fw_days_map[bt_fw2]

        with st.spinner("Download prezzi..."):
            try:
                raw_bt = yf.download(bt_all,
                    start=ref_dt - timedelta(days=3*365),
                    end=datetime.today(), auto_adjust=True, progress=False)
                bt_close = raw_bt["Close"] if isinstance(raw_bt.columns, pd.MultiIndex) else raw_bt
                bt_close = bt_close.dropna(how="all")
            except Exception as e:
                st.error(f"Errore download: {e}")
                st.stop()

        not_found = [t for t in bt_all if t not in bt_close.columns]
        if not_found:
            st.warning(f"Ticker non trovati: {', '.join(not_found)}")
        if bt_benchmark not in bt_close.columns:
            st.error(f"Benchmark {bt_benchmark} non disponibile.")
            st.stop()

        # Data effettiva più vicina disponibile
        actual_ref = bt_close.index[bt_close.index.searchsorted(ref_dt)]
        if actual_ref > bt_close.index[-1]:
            actual_ref = bt_close.index[-1]

        st.markdown(
            f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:6px;'
            f'padding:8px 16px;margin-bottom:10px;font-size:0.82em;color:#888;">'
            f'Data riferimento effettiva: <b style="color:#ff9900">'
            f'{actual_ref.strftime("%d/%m/%Y")}</b></div>',
            unsafe_allow_html=True)

        bt_hist = bt_close[bt_close.index <= actual_ref].copy()
        bm_hist = bt_hist[bt_benchmark].dropna()

        def rsr_at(tk, days):
            try:
                s = bt_hist[tk].dropna()
                b = bm_hist
                if len(s)<=days or len(b)<=days: return np.nan
                rs = float(s.iloc[-1]/s.iloc[-days-1]-1)
                rb = float(b.iloc[-1]/b.iloc[-days-1]-1)
                return float((1+rs)/(1+rb)-1)
            except: return np.nan

        def abs_at(tk, days):
            try:
                s = bt_hist[tk].dropna()
                if len(s)<=days: return np.nan
                return float(s.iloc[-1]/s.iloc[-days-1]-1)
            except: return np.nan

        def fw(tk, days):
            try:
                s = bt_close[tk].dropna()
                i = s.index.searchsorted(actual_ref)
                if i+days >= len(s): return np.nan
                p0,p1 = float(s.iloc[i]), float(s.iloc[i+days])
                if pd.isna(p0) or p0==0: return np.nan
                return p1/p0-1
            except: return np.nan

        wts=[0.20,0.35,0.25,0.20]
        rows=[]
        for tk in bt_tickers:
            if tk not in bt_close.columns: continue
            r1d=rsr_at(tk,1); r1w=rsr_at(tk,5)
            r1m=rsr_at(tk,21); r3m=rsr_at(tk,63); r6m=rsr_at(tk,126)
            vr=[r1w,r1m,r3m,r6m]
            mms6m_rsr = sum(v*w for v,w in zip(vr,wts)) if not any(np.isnan(v) for v in vr) else np.nan
            va=[abs_at(tk,d) for d in [5,21,63,126]]
            mms6m_abs = sum(v*w for v,w in zip(va,wts)) if not any(np.isnan(v) for v in va) else np.nan
            breve = r1m*0.50+r1w*0.35+r1d*0.15 if not any(np.isnan(v) for v in [r1m,r1w,r1d]) else np.nan
            medio = r1m*0.35+r3m*0.25+r6m*0.20+r1w*0.20 if not any(np.isnan(v) for v in [r1m,r3m,r6m,r1w]) else np.nan
            tt  = (breve-medio) if not (np.isnan(breve) or np.isnan(medio)) else np.nan
            mr  = (breve/(abs(medio)+2)) if not (np.isnan(breve) or np.isnan(medio)) else np.nan
            if not np.isnan(mms6m_rsr) and mms6m_rsr>0.03 and not np.isnan(r1w) and not np.isnan(r1m):
                mbi = ((r1w+r1m)/2 - mms6m_rsr)/abs(mms6m_rsr)
            else: mbi = np.nan

            

            ret_fw1 = fw(tk, fwd1_d)
            ret_fw2 = fw(tk, fwd2_d)
            bm_fw1  = fw(bt_benchmark, fwd1_d)
            bm_fw2  = fw(bt_benchmark, fwd2_d)
            d1 = (ret_fw1-bm_fw1) if not (np.isnan(ret_fw1) or np.isnan(bm_fw1)) else np.nan
            d2 = (ret_fw2-bm_fw2) if not (np.isnan(ret_fw2) or np.isnan(bm_fw2)) else np.nan
            # AMSR
            maxdd_rsr = calcola_maxdd_rsr(tk, bt_benchmark, bt_close, actual_ref)
            maxdd_abs = calcola_maxdd_assoluto(tk, bt_close, actual_ref)
            try:
                tk_s = bt_close[tk].dropna()
                ret_abs_1m = float(tk_s.iloc[-1] / tk_s.iloc[-22] - 1) if len(tk_s) > 21 else np.nan
                ret_abs_3m = float(tk_s.iloc[-1] / tk_s.iloc[-64] - 1) if len(tk_s) > 63 else np.nan
            except:
                ret_abs_1m, ret_abs_3m = np.nan, np.nan
            amsr_score = (ret_abs_1m + ret_abs_3m - abs(maxdd_abs)) if not np.isnan(maxdd_abs) else np.nan
            rows.append({
                "Ticker":tk,
                "MMS6M RSr":mms6m_rsr, "MMS6M Ass.":mms6m_abs,
                "Tact. Thrust":tt, "Mr Index":mr, "MBI":mbi,
                "AMSR Score":amsr_score,
                f"Rend +{bt_fw1}":ret_fw1, f"Rend +{bt_fw2}":ret_fw2,
                f"Delta BM +{bt_fw1}":d1,  f"Delta BM +{bt_fw2}":d2,
            })

        if not rows:
            st.warning("Nessun dato calcolato.")
            st.stop()

        res = pd.DataFrame(rows).set_index("Ticker").sort_values("MMS6M RSr", ascending=False)
        # Ranking
        res["Rank MMS6M"] = res["MMS6M RSr"].rank(ascending=False, na_option="bottom").astype(int)
        
        # MBI alert
        mbi_alert = res[res["MBI"].abs() > bt_thr_mbi].dropna(subset=["MBI"])
        if not mbi_alert.empty:
            lst = [f"{t} ({v:+.2f})" for t,v in mbi_alert["MBI"].items()]
            st.markdown(
                f'<div style="background:#1a1000;border:1px solid #554400;border-radius:6px;'
                f'padding:8px 16px;margin-bottom:10px;font-size:0.82em;color:#ffaa00;">'
                f'MBI Alert (|MBI| > {bt_thr_mbi:.2f}): {" · ".join(lst)}</div>',
                unsafe_allow_html=True)

        fw1c=f"Rend +{bt_fw1}"; fw2c=f"Rend +{bt_fw2}"
        d1c=f"Delta BM +{bt_fw1}"; d2c=f"Delta BM +{bt_fw2}"

        def _c_fw(v):
            try:
                v=float(v)
                if np.isnan(v): return "color:#444"
                if v>0.05:  return "color:#00ff55;font-weight:bold"
                if v>0:     return "color:#88cc88"
                if v<-0.05: return "color:#ff4422;font-weight:bold"
                return "color:#cc6644"
            except: return ""

        def _c_dbm(v):
            try:
                v=float(v)
                if np.isnan(v): return "color:#444"
                if v>0.03:  return "color:#00ff55;font-weight:bold"
                if v>0:     return "color:#88cc88"
                if v<-0.03: return "color:#ff4422;font-weight:bold"
                return "color:#cc6644"
            except: return ""

        def _c_seg2(v):
            if "ATTIVO"    in str(v): return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
            if "FILTRATO"  in str(v): return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
            if "WATCHLIST" in str(v): return "background-color:#2b2200;color:#ffaa00;font-weight:bold"
            return ""

        def _c_mms_rsr2(v):
            try:
                v=float(v)
                if v>0.01:  return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
                if v<-0.01: return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
            except: pass
            return "color:#888"

        def _c_mms_abs2(v):
            try:
                v=float(v)
                if v>0.03:  return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
                if v<-0.03: return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
            except: pass
            return "color:#888"

        def _c_tt2(v):
            try:
                v=float(v)
                if v>0.015:  return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
                if v<-0.015: return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
            except: pass
            return "color:#888"

        def _c_mr2(v):
            try:
                v=float(v)
                if v>0.01:  return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
                if v<-0.01: return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
            except: pass
            return "color:#888"

        def _c_mbi2(v):
            try:
                v=float(v)
                if v<-1.00: return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
                if v>1.00:  return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
                if v>0.50:  return "color:#ffaa00"
            except: pass
            return "color:#888"
        def _c_amsr_score(v):
            try:
                v = float(v)
                if np.isnan(v):  return "color:#444"
                if v >= 0.05:    return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
                if v >= 0.02:    return "color:#88cc88"
                if v >= 0:       return "color:#888"
                return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
            except: return ""

        def _c_amsr_sharpe(v):
            try:
                v = float(v)
                if np.isnan(v):  return "color:#444"
                if v > 1.0:      return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
                if v > 0.5:      return "color:#88cc88"
                if v >= 0:       return "color:#888"
                return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
            except: return ""

        def _c_delta_rank(v):
            try:
                v = int(v)
                if v <= -3:  return "color:#00ff55;font-weight:bold"
                if v <= -1:  return "color:#88cc88"
                if v >= 3:   return "color:#ff4422;font-weight:bold"
                if v >= 1:   return "color:#cc6644"
                return "color:#888"
            except: return ""

        fp2 = lambda x: f"{x*100:+.2f}%" if not pd.isna(x) else "N/D"
        fm2 = lambda x: f"{x:+.2f}"      if not pd.isna(x) else "—"

        def _c_gemini2(v):
            try:
                v=float(v)
                if v>0.005:  return "color:#00ff55"
                if v>0:      return "color:#88cc88"
                if v<-0.005: return "color:#ff4422"
                if v<0:      return "color:#cc6644"
            except: pass
            return "color:#888"

        def _c_gte2(v):
            try:
                v=float(v)
                if v>1.0:  return "background-color:#0d2b0d;color:#00ff55;font-weight:bold"
                if v>0.3:  return "color:#88cc88"
                if v>0:    return "color:#aaaaaa"
                if v<-1.0: return "background-color:#2b0d0d;color:#ff4422;font-weight:bold"
                if v<0:    return "color:#cc6644"
            except: pass
            return "color:#888"

        st.dataframe(
            res.style
            .map(_c_mms_abs2,  subset=["MMS6M Ass."])
            .map(_c_mms_rsr2,  subset=["MMS6M RSr"])
            .map(_c_tt2,       subset=["Tact. Thrust"])
            .map(_c_mr2,       subset=["Mr Index"])
            .map(_c_mbi2,      subset=["MBI"])
            .map(_c_fw,        subset=[fw1c,fw2c])
            .map(_c_dbm,       subset=[d1c,d2c])
            .map(_c_amsr_score, subset=["AMSR Score"])
            .format({
                "MMS6M Ass.":   fp2, "MMS6M RSr":    fp2,
                "Tact. Thrust": fp2, "Mr Index":      fp2,
                "MBI":          fm2,
                fw1c: fp2, fw2c: fp2, d1c: fp2, d2c: fp2,
                "AMSR Score":   fp2,
                "Rank MMS6M":   lambda x: f"{int(x)}" if not pd.isna(x) else "-",
            })
        )

        # Riepilogo
        st.markdown(
            f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;'
            f'padding:10px 20px;margin-top:8px;font-size:0.85em;color:#888;'
            f'display:flex;gap:28px;flex-wrap:wrap;">'
            f'<span style="color:#555;">Data: {actual_ref.strftime("%d/%m/%Y")} · Bm: {bt_benchmark} · Settori: {len(res)}</span>'
            f'</div>', unsafe_allow_html=True)

        # Analisi forward sui soli ATTIVI
        attivi = res[res["MMS6M RSr"] > 0].dropna(subset=[fw1c])
        if not attivi.empty:
            st.markdown("---")
            st.markdown("#### Performance forward — settori con GTE positivo")
            avg1=attivi[fw1c].dropna().mean()
            avg2=attivi[fw2c].dropna().mean()
            d1m=attivi[d1c].dropna().mean()
            hit=( attivi[fw1c].dropna()>0).sum()
            n  =attivi[fw1c].dropna().count()
            kk=st.columns(4)
            for col,lbl,val,col_ in [
                (kk[0],f"Rend medio +{bt_fw1}",
                 f"{avg1*100:+.2f}%" if not np.isnan(avg1) else "N/D",
                 "#00ff55" if not np.isnan(avg1) and avg1>0 else "#ff4422"),
                (kk[1],f"Rend medio +{bt_fw2}",
                 f"{avg2*100:+.2f}%" if not np.isnan(avg2) else "N/D",
                 "#00ff55" if not np.isnan(avg2) and avg2>0 else "#ff4422"),
                (kk[2],f"Hit rate +{bt_fw1}",f"{hit}/{n}" if n>0 else "N/D","#ff9900"),
                (kk[3],f"Delta BM medio +{bt_fw1}",
                 f"{d1m*100:+.2f}%" if not np.isnan(d1m) else "N/D",
                 "#00ff55" if not np.isnan(d1m) and d1m>0 else "#ff4422"),
            ]:
                col.markdown(
                    f'<div style="background:#0d0d0d;border:1px solid #222;'
                    f'border-radius:8px;padding:10px 14px;">'
                    f'<div style="color:#555;font-size:0.75em">{lbl}</div>'
                    f'<div style="color:{col_};font-size:1.15em;font-weight:bold">{val}</div>'
                    f'</div>', unsafe_allow_html=True)

    else:
        st.markdown("""
        <div style="background:#080808;border:1px solid #1a1a1a;border-radius:10px;
                    padding:24px;margin-top:8px;color:#555;font-size:0.88em;line-height:1.8;">
        <b style="color:#ff9900">Come usare:</b><br>
        1. Scegli una data storica di riferimento<br>
        2. Modifica ticker/benchmark per altri universi (es. SPDR US)<br>
        3. Calibra le soglie gate con gli slider<br>
        4. Premi <b>Calcola Backtest</b><br>
        5. La tabella mostra indicatori alla data e rendimenti forward effettivi<br><br>
        <b style="color:#ff9900">Gate sequenziale:</b>
        MMS6M Ass. &gt; soglia → MMS6M RSr &gt; soglia → TT &gt; soglia → Mr Index &gt; soglia
        → <b style="color:#00ff55">🟢 ATTIVO</b>
        </div>
        """, unsafe_allow_html=True)
# ========================
# TAB 7 — BACKTEST RS
# ========================
with tab7:
    import json
    st.markdown(
        '<h3 style="color:#ff9900;margin-bottom:4px;">🧪 Backtest Rotation Score — Episodi Risk Off</h3>'
        '<p style="color:#555;font-size:0.82em;margin-top:0;">'
        'Dataset storico 2021–2026 · 5 episodi identificati · Soglia dinamica ~-3.5 · Conferma 5 giorni</p>',
        unsafe_allow_html=True)
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
            col.markdown(f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;padding:10px 14px;margin-bottom:10px;">'
                         f'<div style="color:#555;font-size:0.72em;letter-spacing:0.06em">{label}</div>'
                         f'<div style="color:{color};font-size:1.15em;font-weight:bold">{val}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:6px;padding:8px 16px;margin-bottom:16px;font-size:0.80em;color:#666;">'
                    f'⏱ <b style="color:#ff9900">Timing critico</b>: {bt["statistiche_aggregate"]["nota_timing"]}</div>', unsafe_allow_html=True)

        st.markdown("### 📋 Regole operative")
        ro = bt["regola_operativa"]
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown(f'<div style="background:#0d2b0d;border:1px solid #00cc44;border-radius:8px;padding:14px 16px;">'
                        f'<div style="color:#00ff55;font-size:0.72em;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">✅ Segnale POSITIVO</div>'
                        f'<div style="color:#ccc;font-size:0.85em;line-height:1.6;">{ro["segnale_positivo"]}</div></div>', unsafe_allow_html=True)
        with col_r2:
            st.markdown(f'<div style="background:#2b0d0d;border:1px solid #cc2200;border-radius:8px;padding:14px 16px;">'
                        f'<div style="color:#ff4422;font-size:0.72em;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">❌ Segnale NEGATIVO</div>'
                        f'<div style="color:#ccc;font-size:0.85em;line-height:1.6;">{ro["segnale_negativo"]}</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 1 · Episodi storici")
        colori_pattern = {"A": "#ff4422", "B": "#ffaa00", "C": "#44aaff", "D": "#ffff44"}
        colori_esito   = {"positivo_forte": "#00ff55", "positivo": "#88cc88",
                          "positivo_lento": "#ffaa00", "negativo": "#ff4422"}
        rows_bt = []
        for ep in bt["episodi"]:
            ind = ep["indicatori"]
            top = ep["top_successivo"]
            rows_bt.append({"Ep": ep["id"], "Pattern": ep["pattern"], "RS inizio": ep["rs_inizio"],
                             "RS bottom": ep["rs_bottom_date"], "RS min": ep["rs_min"],
                             "Durata (gg)": ep["durata_gg"], "SPY bottom": ep["spy_bottom_date"],
                             "Δ RS→SPY(gg)": ep["delta_rs_spy_gg"], "SPY +20gg": ep["spy_perf_20"],
                             "SPY +40gg": ep["spy_perf_40"], "VIX": ind["vix"],
                             "MOVE": ind["move"] if ind["move"] else "n/d", "IEF-SHY": ind["ief_shy"],
                             "Top qualità": top["qualita"], "Esito": ep["esito"]})
        bt_df = pd.DataFrame(rows_bt)

        def style_pattern_col(val):  return f"color:{colori_pattern.get(str(val), '#888')};font-weight:bold"
        def style_esito_col(val):    return f"color:{colori_esito.get(str(val), '#888')};font-weight:bold"
        def style_delta(val):
            try:
                v = float(val)
                if v < 0:  return "color:#44aaff;font-weight:bold"
                if v > 40: return "color:#ff4422"
                return "color:#888"
            except Exception: return ""
        def style_rs_min_bt(val):
            try:
                v = float(val)
                if v < -8: return "color:#ff4422;font-weight:bold"
                if v < -6: return "color:#ffaa00;font-weight:bold"
                return "color:#888"
            except Exception: return ""
        def style_top_qualita(val):
            if str(val) == "VERO":    return "color:#00ff55;font-weight:bold"
            if str(val) == "TECNICO": return "color:#ffaa00;font-weight:bold"
            return ""

        st.dataframe(bt_df.style
            .map(style_pattern_col, subset=["Pattern"]).map(style_esito_col, subset=["Esito"])
            .map(style_delta, subset=["Δ RS→SPY(gg)"]).map(style_rs_min_bt, subset=["RS min"])
            .map(style_top_qualita, subset=["Top qualità"])
            .format({"RS min": "{:.2f}", "SPY +20gg": "{:+.2f}%", "SPY +40gg": "{:+.2f}%", "IEF-SHY": "{:.2f}"}),
            use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 2 · Pattern di riferimento")
        pattern_cols = st.columns(4)
        for i, pid in enumerate(["A","B","C","D"]):
            p = bt["pattern"][pid]
            cond_str = " · ".join([f"{k.upper()} {v}" for k, v in p["condizioni"].items()])
            color = colori_pattern[pid]
            with pattern_cols[i]:
                st.markdown(
                    f'<div style="background:#0d0d0d;border:1px solid {color}33;border-top:3px solid {color};'
                    f'border-radius:8px;padding:14px;height:100%;">'
                    f'<div style="color:{color};font-size:1.1em;font-weight:bold;margin-bottom:6px;">Pattern {pid}</div>'
                    f'<div style="color:#ff9900;font-size:0.82em;font-weight:bold;margin-bottom:8px;">{p["nome"]}</div>'
                    f'<div style="color:#555;font-size:0.72em;margin-bottom:8px;">{cond_str}</div>'
                    f'<div style="color:#aaa;font-size:0.78em;line-height:1.5;margin-bottom:8px;">{p["descrizione"]}</div>'
                    f'<div style="color:{color};font-size:0.75em;font-style:italic;">↗ {p["payoff_atteso"]}</div></div>',
                    unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 3 · Note analitiche per episodio")
        for ep in bt["episodi"]:
            color = colori_pattern.get(ep["pattern"], "#888")
            with st.expander(f"Ep.{ep['id']} — {ep['rs_inizio']}  |  Pattern {ep['pattern']}  |  "
                             f"RS min: {ep['rs_min']}  |  SPY +40gg: {ep['spy_perf_40']:+.2f}%", expanded=False):
                st.markdown(f'<div style="background:#080808;border-left:3px solid {color};'
                            f'padding:12px 16px;border-radius:0 6px 6px 0;font-size:0.85em;color:#aaa;line-height:1.7;">'
                            f'{ep["note"]}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 4 · Regola qualità top")
        rqt = bt["regola_qualita_top"]
        st.markdown(f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;padding:14px 20px;font-size:0.85em;line-height:1.8;">'
                    f'<b style="color:#00ff55">Top VERO</b>: {rqt["top_vero"]}<br>'
                    f'<b style="color:#ffaa00">Top TECNICO</b>: {rqt["top_tecnico"]}<br>'
                    f'<span style="color:#555">{rqt["implicazione"]}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#0a0a0a;border:1px solid #1a1a1a;border-radius:6px;'
                    f'padding:8px 16px;margin-top:16px;font-size:0.75em;color:#444;">'
                    f'📅 Dati aggiornati al: <b style="color:#ff9900">{bt["metadata"]["aggiornato"]}</b> · '
                    f'Per aggiornare: modifica <b>backtest_patterns.json</b> nel repo e fai commit</div>',
                    unsafe_allow_html=True)

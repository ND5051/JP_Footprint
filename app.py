"""
JP Footprint — NSE & BSE end-of-day dashboard
=============================================
A "JP day" = a session whose HIGH ends in 9.90 or 9.95 (e.g. 409.90, 469.95).
For every JP day we show 12% above and 12% below the JP high; we find the
nearest JP above and below the latest close (resistance / support); and we mark
days where Open == High on a JP day. Data is adjusted EOD from Yahoo Finance.

Run locally:   streamlit run app.py
"""

import io
import datetime as dt

import pandas as pd
import requests
import streamlit as st

from jp_core import inr, indian_num, is_jp, resample, analyse

# --------------------------------------------------------------------------- #
#  Page setup
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="JP Footprint", page_icon="👣", layout="wide")

NSE_BLUE = "#4f46e5"
BSE_AMBER = "#d97706"

# --------------------------------------------------------------------------- #
#  Instrument universe (cached 24h) with graceful fallback
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=86400, show_spinner=False)
def load_nse_list():
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = [c.strip() for c in df.columns]
    out = pd.DataFrame({
        "name": df["NAME OF COMPANY"].str.strip(),
        "nse_symbol": df["SYMBOL"].str.strip() + ".NS",
        "isin": df["ISIN NUMBER"].str.strip(),
    })
    return out


@st.cache_data(ttl=86400, show_spinner=False)
def load_bse_list():
    url = ("https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?"
           "Group=&Scripcode=&industry=&segment=Equity&status=Active")
    headers = {"User-Agent": "Mozilla/5.0",
               "Referer": "https://www.bseindia.com/",
               "Accept": "application/json"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    rows = []
    for item in data:
        keys = {k.lower(): v for k, v in item.items()}
        sid = keys.get("scrip_id") or keys.get("scripid")
        name = keys.get("scrip_name") or keys.get("scripname")
        isin = keys.get("isin_number") or keys.get("isin")
        if sid and name:
            rows.append({"name": str(name).strip(),
                         "bse_symbol": str(sid).strip() + ".BO",
                         "isin": str(isin).strip() if isin else ""})
    return pd.DataFrame(rows)


@st.cache_data(ttl=86400, show_spinner=True)
def load_universe():
    """Merge NSE + BSE by ISIN. Fall back to a bundled curated list on failure."""
    notes = []
    nse = bse = None
    try:
        nse = load_nse_list()
    except Exception as e:  # noqa: BLE001
        notes.append("NSE list unavailable")
    try:
        bse = load_bse_list()
    except Exception as e:  # noqa: BLE001
        notes.append("BSE list unavailable")

    if nse is None and bse is None:
        fb = pd.read_csv("fallback_instruments.csv")
        return fb, ["Using bundled fallback list (live exchange lists "
                    "couldn't be reached just now)."]

    if nse is not None and bse is not None:
        m = pd.merge(nse, bse[bse["isin"] != ""], on="isin", how="outer")
        m["name"] = m["name_x"].fillna(m["name_y"])
        m = m[["name", "nse_symbol", "bse_symbol", "isin"]]
    elif nse is not None:
        m = nse.copy()
        m["bse_symbol"] = pd.NA
    else:
        m = bse.copy()
        m["nse_symbol"] = pd.NA

    m = m.dropna(subset=["name"]).drop_duplicates(subset=["name"])
    m = m.sort_values("name").reset_index(drop=True)
    return m, notes


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_history(symbol, start):
    """Adjusted daily OHLCV from Yahoo Finance, or None."""
    import yfinance as yf
    df = yf.Ticker(symbol).history(start=start, interval="1d", auto_adjust=True)
    if df is None or df.empty:
        return None
    df = df.reset_index()[["Date", "Open", "High", "Low", "Close", "Volume"]]
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    return df


# --------------------------------------------------------------------------- #
#  Rendering
# --------------------------------------------------------------------------- #
def ladder_html(close, above, below, accent):
    if above is None or below is None:
        return ""
    lo = below["High"] * 0.88
    hi = above["High"] * 1.12
    span = (hi - lo) or 1
    pct = lambda v: max(0, min(100, (v - lo) / span * 100))
    s, r, now = pct(below["High"]), pct(above["High"]), pct(close)
    return f"""
    <div style="border:1px solid #e2e8f0;border-radius:8px;padding:12px;background:#fff">
      <div style="display:flex;justify-content:space-between;font-size:11px;
           text-transform:uppercase;letter-spacing:.04em;color:#94a3b8;margin-bottom:10px">
        <span>Price vs nearest JP levels</span>
        <span style="font-variant-numeric:tabular-nums;color:#475569">close {inr(close)}</span>
      </div>
      <div style="position:relative;height:10px;border-radius:9999px;background:#f1f5f9">
        <div style="position:absolute;top:0;bottom:0;left:0;width:{s}%;background:#d1fae5;border-radius:9999px 0 0 9999px"></div>
        <div style="position:absolute;top:0;bottom:0;left:{r}%;right:0;background:#ffe4e6;border-radius:0 9999px 9999px 0"></div>
        <div style="position:absolute;top:-2px;height:14px;width:2px;background:#10b981;left:{s}%"></div>
        <div style="position:absolute;top:-2px;height:14px;width:2px;background:#f43f5e;left:{r}%"></div>
        <div style="position:absolute;top:-6px;left:{now}%;margin-left:-6px;width:0;height:0;
             border-left:6px solid transparent;border-right:6px solid transparent;border-top:8px solid {accent}"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:11px;
           font-variant-numeric:tabular-nums;margin-top:8px">
        <span style="color:#047857">support {inr(below['High'])} · {below['Date'].strftime('%d-%b-%y')}</span>
        <span style="color:#be123c">resistance {inr(above['High'])} · {above['Date'].strftime('%d-%b-%y')}</span>
      </div>
    </div>"""


def nearest_card(kind, jp):
    is_res = kind == "resistance"
    label = ("Nearest JP above close · resistance" if is_res
             else "Nearest JP below close · support")
    if jp is None:
        st.markdown(f"<div style='border:1px solid #e2e8f0;border-radius:8px;"
                    f"padding:12px;background:#fff;font-size:13px;color:#94a3b8'>"
                    f"{label}<br>No JP level on this side.</div>",
                    unsafe_allow_html=True)
        return
    oh = ("<span style='float:right;background:#ede9fe;color:#6d28d9;border-radius:4px;"
          "padding:1px 6px;font-size:10px;font-weight:600'>O = H ↔</span>") if jp["oh"] else ""
    cells = [("JP date", jp["Date"].strftime("%d-%b-%y")),
             ("JP high", inr(jp["High"])),
             ("+12% high", inr(jp["High"] * 1.12)),
             ("JP low", inr(jp["Low"])),
             ("-12% high", inr(jp["High"] * 0.88))]
    body = "".join(
        f"<div><div style='font-size:10px;color:#94a3b8'>{k}</div>"
        f"<div style='font-variant-numeric:tabular-nums;font-size:13px;"
        f"font-weight:500;color:#1e293b'>{v}</div></div>" for k, v in cells)
    ring = "#fecdd3" if is_res else "#a7f3d0"
    st.markdown(
        f"<div style='border:1px solid {ring};border-radius:8px;padding:12px;background:#fff'>"
        f"<div style='font-size:11px;text-transform:uppercase;letter-spacing:.04em;"
        f"color:#64748b'>{label}{oh}</div>"
        f"<div style='display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:8px'>"
        f"{body}</div></div>", unsafe_allow_html=True)


def style_jp(jp):
    show = jp[["Year", "Date", "High", "oh", "above12", "Low", "below12"]].copy()
    show["Date"] = show["Date"].dt.strftime("%d-%b-%y")
    show["oh"] = show["oh"].map({True: "↔", False: ""})
    show = show.rename(columns={"oh": "O=H", "above12": "+12% High",
                                "below12": "-12% High"})
    oh_mask = (show["O=H"] == "↔").values

    def row_color(col):
        return ["background-color:#f5f3ff" if o else "" for o in oh_mask]

    sty = (show.style
           .apply(row_color, axis=0)
           .format({"High": "₹{:.2f}", "+12% High": "₹{:.2f}",
                    "Low": "₹{:.2f}", "-12% High": "₹{:.2f}", "Year": "{:.0f}"})
           .set_properties(subset=["+12% High"], **{"color": "#e11d48"})
           .set_properties(subset=["-12% High"], **{"color": "#047857"}))
    return sty


def style_daily(df, min3, min5):
    show = df.sort_values("Date", ascending=False).copy()
    show["JP"] = show["High"].apply(lambda h: "JP" if is_jp(h) else "")
    show["Date"] = show["Date"].dt.strftime("%d-%b-%y")
    show["Volume"] = show["Volume"].apply(indian_num)
    show = show[["Date", "Open", "High", "Low", "Close", "Volume", "JP"]]
    lows = df.sort_values("Date", ascending=False)["Low"].values
    low_flags = []
    for i, lv in enumerate(lows):
        if i < 5 and lv == min5:
            low_flags.append("background-color:#fecdd3;font-weight:600;color:#9f1239")
        elif i < 3 and lv == min3:
            low_flags.append("background-color:#ffe4e6;color:#be123c")
        else:
            low_flags.append("")

    sty = (show.style
           .apply(lambda c: low_flags, axis=0, subset=["Low"])
           .format({"Open": "₹{:.2f}", "High": "₹{:.2f}",
                    "Low": "₹{:.2f}", "Close": "₹{:.2f}"}))
    return sty


def exchange_panel(symbol, label, accent, start, tf):
    st.markdown(
        f"<div style='background:{accent};color:#fff;padding:8px 14px;border-radius:8px 8px 0 0;"
        f"font-weight:600;font-size:14px'>🏛 {label} "
        f"<span style='float:right;font-weight:400;opacity:.9;font-size:11px;"
        f"font-variant-numeric:tabular-nums'>{symbol}</span></div>",
        unsafe_allow_html=True)
    with st.container(border=True):
        raw = fetch_history(symbol, start)
        if raw is None:
            st.warning(f"No data returned for {symbol}. Yahoo may be rate-limiting "
                       "or the symbol isn't available — try again shortly.")
            return
        df = resample(raw, tf)
        if len(df) < 2:
            st.info("Not enough candles for this timeframe yet.")
            return
        a = analyse(df)
        st.markdown(ladder_html(a["close"], a["above"], a["below"], accent),
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            nearest_card("resistance", a["above"])
        with c2:
            nearest_card("support", a["below"])
        st.caption(f"JP days ({tf.lower()}) — highlighted row = Open equals High")
        if len(a["jp"]):
            st.dataframe(style_jp(a["jp"]), hide_index=True, use_container_width=True)
        else:
            st.caption("No JP days found in this range.")
        st.caption("Daily prices — Low shaded for 3-day (light) / 5-day (dark) low")
        st.dataframe(style_daily(df, a["min3"], a["min5"]),
                     hide_index=True, use_container_width=True, height=320)


# --------------------------------------------------------------------------- #
#  App
# --------------------------------------------------------------------------- #
st.markdown("### 👣 JP Footprint")
st.caption("NSE & BSE · end-of-day · a JP day = a session whose high ends in 9.90 or 9.95")

universe, notes = load_universe()
for n in notes:
    st.info(n)

c1, c2, c3 = st.columns([3, 1.4, 1.6])
with c1:
    names = universe["name"].dropna().tolist()
    default = names.index("GUJARAT GAS LIMITED") if "GUJARAT GAS LIMITED" in names else 0
    pick = st.selectbox("Stock (type to search)", names,
                        index=default if names else None)
with c2:
    start = st.date_input("Start date", dt.date(2020, 1, 1),
                          min_value=dt.date(2000, 1, 1), max_value=dt.date.today())
with c3:
    tf = st.radio("Timeframe", ["Daily", "Weekly", "Monthly"], horizontal=True)

row = universe[universe["name"] == pick].iloc[0]
nse_sym = row.get("nse_symbol")
bse_sym = row.get("bse_symbol")
nse_sym = nse_sym if isinstance(nse_sym, str) and nse_sym.endswith(".NS") else None
bse_sym = bse_sym if isinstance(bse_sym, str) and bse_sym.endswith(".BO") else None

# If only NSE is known, probe the matching .BO ticker for a dual listing.
if nse_sym and not bse_sym:
    cand = nse_sym.replace(".NS", ".BO")
    if fetch_history(cand, dt.date.today() - dt.timedelta(days=14)) is not None:
        bse_sym = cand

listed = [x for x in (("NSE", nse_sym), ("BSE", bse_sym)) if x[1]]
st.write("")

if not listed:
    st.error("No tradable Yahoo Finance symbol found for this stock.")
elif len(listed) == 2:
    colA, colB = st.columns(2)
    with colA:
        exchange_panel(nse_sym, "NSE — National Stock Exchange", NSE_BLUE, start, tf)
    with colB:
        exchange_panel(bse_sym, "BSE — Bombay Stock Exchange", BSE_AMBER, start, tf)
else:
    name, sym = listed[0]
    accent = NSE_BLUE if name == "NSE" else BSE_AMBER
    full = "NSE — National Stock Exchange" if name == "NSE" else "BSE — Bombay Stock Exchange"
    exchange_panel(sym, full, accent, start, tf)

st.caption("Adjusted EOD data via Yahoo Finance, cached daily. For research only — "
           "not investment advice.")

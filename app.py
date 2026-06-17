"""
JP Footprint — NSE & BSE end-of-day dashboard.

A "JP day" = a session whose HIGH ends in 9.90 or 9.95 (e.g. 409.90, 469.95).
For every JP day we show 12% above/below the JP high, the nearest JP above and
below the latest close (resistance / support), and mark days where Open == High.

Data: NSE via nselib, BSE via bseindia (no account). Run: streamlit run app.py
"""
import datetime as dt

import pandas as pd
import streamlit as st

import data_sources as ds
from jp_core import inr, indian_num, is_jp, resample, analyse

st.set_page_config(page_title="JP Footprint", page_icon="👣", layout="wide")

NSE_BLUE = "#4f46e5"
BSE_AMBER = "#d97706"
JP_COLS = ["Year", "Date", "High", "O=H", "+12% High", "Low", "-12% High"]
DAILY_COLS = ["Date", "Open", "High", "Low", "Close", "Volume", "JP"]
JP_H = 388     # ~10 rows then scroll
DAILY_H = 360  # fixed, scrolls


@st.cache_data(ttl=86400, show_spinner="Loading NSE + BSE instruments…")
def load_universe():
    return ds.load_universe_or_fallback("bhavcopies", "fallback_instruments.csv")


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_nse(symbol, start, end):
    return ds.fetch_nse_history(symbol, start, end)


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_bse(code, start, end):
    return ds.fetch_bse_history(code, start, end)


# --------------------------------------------------------------------------- #
#  Boxes (always rendered, empty when no data)
# --------------------------------------------------------------------------- #
def ladder_html(close, above, below, accent):
    head = ("<div style='display:flex;justify-content:space-between;font-size:11px;"
            "text-transform:uppercase;letter-spacing:.04em;color:#94a3b8;margin-bottom:10px'>"
            "<span>Price vs nearest JP levels</span>"
            f"<span style='font-variant-numeric:tabular-nums;color:#475569'>"
            f"{'close ' + inr(close) if close is not None else '&nbsp;'}</span></div>")
    box = "border:1px solid #e2e8f0;border-radius:8px;padding:12px;background:#fff"
    if above is None or below is None or close is None:
        track = ("<div style='position:relative;height:10px;border-radius:9999px;"
                 "background:#f1f5f9'></div>")
        foot = ("<div style='display:flex;justify-content:space-between;font-size:11px;"
                "color:#cbd5e1;margin-top:8px'><span>support —</span>"
                "<span>resistance —</span></div>")
        return f"<div style='{box}'>{head}{track}{foot}</div>"
    lo, hi = below["High"] * 0.88, above["High"] * 1.12
    span = (hi - lo) or 1
    p = lambda v: max(0, min(100, (v - lo) / span * 100))
    s, r, now = p(below["High"]), p(above["High"]), p(close)
    return f"""<div style='{box}'>{head}
      <div style="position:relative;height:10px;border-radius:9999px;background:#f1f5f9">
        <div style="position:absolute;inset-block:0;left:0;width:{s}%;background:#d1fae5;border-radius:9999px 0 0 9999px"></div>
        <div style="position:absolute;inset-block:0;left:{r}%;right:0;background:#ffe4e6;border-radius:0 9999px 9999px 0"></div>
        <div style="position:absolute;top:-2px;height:14px;width:2px;background:#10b981;left:{s}%"></div>
        <div style="position:absolute;top:-2px;height:14px;width:2px;background:#f43f5e;left:{r}%"></div>
        <div style="position:absolute;top:-6px;left:{now}%;margin-left:-6px;width:0;height:0;
             border-left:6px solid transparent;border-right:6px solid transparent;border-top:8px solid {accent}"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:11px;font-variant-numeric:tabular-nums;margin-top:8px">
        <span style="color:#047857">support {inr(below['High'])} · {below['Date'].strftime('%d-%b-%y')}</span>
        <span style="color:#be123c">resistance {inr(above['High'])} · {above['Date'].strftime('%d-%b-%y')}</span>
      </div></div>"""


def nearest_card(kind, jp):
    is_res = kind == "resistance"
    label = ("Nearest JP above close · resistance" if is_res
             else "Nearest JP below close · support")
    ring = "#fecdd3" if is_res else "#a7f3d0"
    box = f"border:1px solid {ring};border-radius:8px;padding:12px;background:#fff;min-height:74px"
    if jp is None:
        cells = [("JP date", "—"), ("JP high", "—"), ("+12% high", "—"),
                 ("JP low", "—"), ("-12% high", "—")]
        oh = ""
    else:
        cells = [("JP date", jp["Date"].strftime("%d-%b-%y")), ("JP high", inr(jp["High"])),
                 ("+12% high", inr(jp["High"] * 1.12)), ("JP low", inr(jp["Low"])),
                 ("-12% high", inr(jp["High"] * 0.88))]
        oh = ("<span style='float:right;background:#ede9fe;color:#6d28d9;border-radius:4px;"
              "padding:1px 6px;font-size:10px;font-weight:600'>O = H ↔</span>"
              if jp["oh"] else "")
    body = "".join(
        f"<div><div style='font-size:10px;color:#94a3b8'>{k}</div>"
        f"<div style='font-variant-numeric:tabular-nums;font-size:13px;font-weight:500;"
        f"color:#1e293b'>{v}</div></div>" for k, v in cells)
    st.markdown(
        f"<div style='{box}'><div style='font-size:11px;text-transform:uppercase;"
        f"letter-spacing:.04em;color:#64748b'>{label}{oh}</div>"
        f"<div style='display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:8px'>"
        f"{body}</div></div>", unsafe_allow_html=True)


def _money(v):
    return f"₹{v:,.2f}"


def _html_table(columns, aligns, rows_html, height):
    head = "".join(
        f"<th style='position:sticky;top:0;z-index:1;background:#f8fafc;padding:8px 12px;"
        f"text-align:{al};font-size:11px;font-weight:600;color:#475569;letter-spacing:.02em;"
        f"border-bottom:1px solid #e2e8f0'>{c}</th>"
        for c, al in zip(columns, aligns))
    return (f"<div style='height:{height}px;overflow:auto;border:1px solid #e2e8f0;"
            f"border-radius:8px;background:#fff'>"
            f"<table style='width:100%;border-collapse:collapse;font-size:13px;"
            f"font-variant-numeric:tabular-nums'>"
            f"<thead><tr>{head}</tr></thead><tbody>{rows_html}</tbody></table></div>")


def _row(cells, tr_style=""):
    tds = "".join(
        f"<td style='padding:6px 12px;text-align:{al};white-space:nowrap;{cs}'>{val}</td>"
        for val, al, cs in cells)
    return f"<tr style='border-top:1px solid #f1f5f9;{tr_style}'>{tds}</tr>"


def jp_table(a):
    cols = JP_COLS  # Year, Date, High, O=H, +12% High, Low, -12% High
    al = ["right", "left", "right", "center", "right", "right", "right"]
    rows = ""
    if a is not None and len(a["jp"]):
        for _, r in a["jp"].iterrows():
            oh = bool(r["oh"])
            tr = "background:#f3effe;" if oh else ""
            cells = [
                (f"{int(r['Year'])}", al[0], "color:#94a3b8"),
                (r["Date"].strftime("%d-%b-%y"), al[1], ""),
                (_money(r["High"]), al[2], "font-weight:600"),
                ("◆" if oh else "", al[3], "color:#7c3aed;font-weight:700;font-size:14px"),
                (_money(r["High"] * 1.12), al[4], "color:#e11d48"),
                (_money(r["Low"]), al[5], ""),
                (_money(r["High"] * 0.88), al[6], "color:#047857"),
            ]
            rows += _row(cells, tr)
    st.markdown(_html_table(cols, al, rows, JP_H), unsafe_allow_html=True)


def daily_table(df, a):
    cols = DAILY_COLS  # Date, Open, High, Low, Close, Volume, JP
    al = ["left", "right", "right", "right", "right", "right", "center"]
    rows = ""
    if df is not None and len(df):
        d = df.sort_values("Date", ascending=False).reset_index(drop=True)
        min3 = a["min3"] if a else None
        min5 = a["min5"] if a else None
        for i, r in d.iterrows():
            jp = is_jp(r["High"])
            tr = "background:#eef2ff;" if jp else ""
            lv = r["Low"]
            low_cs = ""
            if min5 is not None and i < 5 and lv == min5:
                low_cs = "background:#fb9aae;color:#7f1d34;font-weight:700"
            elif min3 is not None and i < 3 and lv == min3:
                low_cs = "background:#ffe1e6;color:#be123c;font-weight:600"
            vol = indian_num(r["Volume"]) if pd.notna(r["Volume"]) else ""
            cells = [
                (r["Date"].strftime("%d-%b-%y"), al[0], ""),
                (_money(r["Open"]), al[1], ""),
                (_money(r["High"]), al[2], ""),
                (_money(r["Low"]), al[3], low_cs),
                (_money(r["Close"]), al[4], "font-weight:600"),
                (vol, al[5], "color:#64748b"),
                ("JP" if jp else "", al[6], "color:#4f46e5;font-weight:700"),
            ]
            rows += _row(cells, tr)
    st.markdown(_html_table(cols, al, rows, DAILY_H), unsafe_allow_html=True)


def exchange_panel(symbol, label, accent, start, end, tf, fetch_fn):
    st.markdown(
        f"<div style='background:{accent};color:#fff;padding:8px 14px;border-radius:8px 8px 0 0;"
        f"font-weight:600;font-size:14px'>🏛 {label}"
        f"<span style='float:right;font-weight:400;opacity:.9;font-size:11px;"
        f"font-variant-numeric:tabular-nums'>{symbol or '—'}</span></div>",
        unsafe_allow_html=True)
    with st.container(border=True):
        df = a = None
        note = ""
        if not symbol:
            note = "No listing on this exchange."
        else:
            try:
                raw = fetch_fn(symbol, start, end)
                df = resample(raw, tf) if raw is not None and len(raw) >= 2 else None
                if df is not None:
                    a = analyse(df)
                elif raw is not None:
                    note = "Not enough candles for this timeframe."
                else:
                    note = "No data returned."
            except ds.DataError:
                note = "Couldn't reach the exchange right now — it may be rate-limiting or blocking this host. Try again shortly."

        st.markdown(ladder_html(a["close"] if a else None,
                                a["above"] if a else None,
                                a["below"] if a else None, accent), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            nearest_card("resistance", a["above"] if a else None)
        with c2:
            nearest_card("support", a["below"] if a else None)
        if note:
            st.caption(f"ⓘ {note}")
        st.caption("JP days — highlighted row = Open equals High")
        jp_table(a)
        st.caption("Daily prices — Low shaded for 3-day (light) / 5-day (dark) low")
        daily_table(df, a)


# --------------------------------------------------------------------------- #
#  App
# --------------------------------------------------------------------------- #
st.markdown("### 👣 JP Footprint")

universe, notes = load_universe()
for n in notes:
    st.info(n)

c1, c2, c3 = st.columns([3, 1.4, 1.6])
with c1:
    names = universe["name"].dropna().tolist()
    default = names.index("GUJARAT GAS LIMITED") if "GUJARAT GAS LIMITED" in names else 0
    pick = st.selectbox("Stock (type to search)", names, index=default if names else None)
with c2:
    start = st.date_input("Start date", dt.date(2020, 1, 1),
                          min_value=dt.date(1995, 1, 1), max_value=dt.date.today())
with c3:
    tf = st.radio("Timeframe", ["Daily", "Weekly", "Monthly"], horizontal=True)

end = dt.date.today()
row = universe[universe["name"] == pick].iloc[0]


def _val(col):
    v = row.get(col)
    return None if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).lower() in ("nan", "none", "") else str(v)


nse_symbol, bse_code = _val("nse_symbol"), _val("bse_code")
st.write("")

colA, colB = st.columns(2)
with colA:
    exchange_panel(nse_symbol, "NSE — National Stock Exchange", NSE_BLUE,
                   start, end, tf, fetch_nse)
with colB:
    exchange_panel(bse_code, "BSE — Bombay Stock Exchange", BSE_AMBER,
                   start, end, tf, fetch_bse)

st.caption("Data for research only — not investment advice.")

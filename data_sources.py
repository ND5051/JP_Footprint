"""
Data layer — both exchanges, no account, via RuchiTanmay's libraries:
  • NSE  -> nselib  (capital_market.price_volume_and_deliverable_position_data, equity_list)
  • BSE  -> bseindia (equity.historical_stock_data, all_listed_securities)

Both return pandas DataFrames with different column names, so df_to_ohlcv()
normalises by keyword and deliberately avoids decoy columns
(PrevClose, Spread High-Low, Deliverable Qty, Turnover, WAP, Average, 52-week…).

No Streamlit import here, so this stays unit-testable.
"""
import datetime as dt
import re

import pandas as pd

DMY = "%d-%m-%Y"


class DataError(Exception):
    """Any failure fetching data (network, rate-limit, blocked host, bad symbol)."""


# --------------------------------------------------------------------------- #
#  Column normalisation
# --------------------------------------------------------------------------- #
def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _pick(columns, needles, avoid=()):
    for c in columns:
        nc = _norm(c)
        if any(a in nc for a in avoid):
            continue
        if any(n in nc for n in needles):
            return c
    return None


def df_to_ohlcv(df):
    """Normalise an NSE/BSE price-volume frame into Date/Open/High/Low/Close/Volume."""
    if df is None or len(df) == 0:
        return None
    cols = list(df.columns)
    cmap = {
        "Date":   _pick(cols, ["date", "timestamp"], avoid=("update",)),
        "Open":   _pick(cols, ["open"], avoid=("spread", "prev")),
        "High":   _pick(cols, ["high"], avoid=("spread", "52", "week")),
        "Low":    _pick(cols, ["low"], avoid=("spread", "52", "week")),
        "Close":  _pick(cols, ["clos"], avoid=("spread", "prev")),
        "Volume": _pick(cols, ["shar", "quant", "qty", "volume"],
                        avoid=("deliver", "turnover", "val")),
    }
    if not all(cmap[k] for k in ("Date", "Open", "High", "Low", "Close")):
        return None
    out = pd.DataFrame({k: df[v] for k, v in cmap.items() if v})
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce", dayfirst=True)
    for c in ("Open", "High", "Low", "Close", "Volume"):
        if c in out:
            out[c] = pd.to_numeric(
                out[c].astype(str).str.replace(",", "", regex=False), errors="coerce")
    if "Volume" not in out:
        out["Volume"] = 0
    out = (out.dropna(subset=["Date", "Open", "High", "Low", "Close"])
              .drop_duplicates("Date").sort_values("Date").reset_index(drop=True))
    return out if len(out) else None


# --------------------------------------------------------------------------- #
#  Universe (NSE + BSE masters, merged by ISIN)
# --------------------------------------------------------------------------- #
def _read_bhav(path):
    """Read a UDiFF bhavcopy CSV (NSE is comma-, BSE is semicolon-separated)."""
    import io
    with io.open(path, encoding="utf-8", errors="ignore") as f:
        head = f.readline()
    sep = ";" if head.count(";") > head.count(",") else ","
    df = pd.read_csv(path, sep=sep, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    return df


def build_universe_from_bhavcopies(folder):
    """Build (DataFrame[name, nse_symbol, bse_code, isin], date_str) from bhavcopy
    files in `folder`. Equities only (ISIN starting 'INE'). Returns (None, None)
    if no usable files are found."""
    import glob
    import os
    import re

    def _filedate(p):
        m = re.search(r"(\d{8})", os.path.basename(p))
        return m.group(1) if m else "0"

    nse_files, bse_files = [], []
    for p in glob.glob(os.path.join(folder, "*")):
        if not p.lower().endswith(".csv"):
            continue
        nm = os.path.basename(p).upper()
        try:
            d = _read_bhav(p)
        except Exception:  # noqa: BLE001
            continue
        if "ISIN" not in d.columns or "TckrSymb" not in d.columns:
            continue
        src = (d["Src"].iloc[0].upper() if "Src" in d.columns and len(d) else "")
        if "NSE" in nm or src == "NSE":
            nse_files.append((p, d))
        elif "BSE" in nm or src == "BSE":
            bse_files.append((p, d))

    nse_files.sort(key=lambda t: _filedate(t[0]), reverse=True)
    bse_files.sort(key=lambda t: _filedate(t[0]), reverse=True)
    nse_d = nse_files[0][1] if nse_files else None
    bse_d = bse_files[0][1] if bse_files else None
    if nse_d is None and bse_d is None:
        return None, None

    nse_u = bse_u = None
    date_str = None
    if nse_d is not None:
        n = nse_d[nse_d["ISIN"].str.startswith("INE", na=False)]
        if "SctySrs" in n.columns:
            n = n[n["SctySrs"].isin(["EQ", "BE", "SM", "ST"])]
        nse_u = (pd.DataFrame({"name": n["FinInstrmNm"].str.strip(),
                               "nse_symbol": n["TckrSymb"].str.strip(),
                               "isin": n["ISIN"].str.strip()})
                 .drop_duplicates("isin"))
        if "TradDt" in nse_d.columns and len(nse_d):
            date_str = str(nse_d["TradDt"].iloc[0])
    if bse_d is not None:
        b = bse_d[bse_d["ISIN"].str.startswith("INE", na=False)]
        if "FinInstrmTp" in b.columns:
            b = b[b["FinInstrmTp"] == "STK"]
        bse_u = (pd.DataFrame({"name_b": b["FinInstrmNm"].str.strip(),
                               "bse_code": b["FinInstrmId"].str.strip(),
                               "isin": b["ISIN"].str.strip()})
                 .drop_duplicates("isin"))
        if date_str is None and "TradDt" in bse_d.columns and len(bse_d):
            date_str = str(bse_d["TradDt"].iloc[0])

    if nse_u is not None and bse_u is not None:
        m = pd.merge(nse_u, bse_u, on="isin", how="outer")
        m["name"] = m["name"].fillna(m["name_b"])
    elif nse_u is not None:
        m = nse_u.copy()
        m["bse_code"] = None
    else:
        m = bse_u.rename(columns={"name_b": "name"}).copy()
        m["nse_symbol"] = None

    m = (m[["name", "nse_symbol", "bse_code", "isin"]]
         .dropna(subset=["name"]).drop_duplicates("isin")
         .sort_values("name").reset_index(drop=True))
    return (m if len(m) else None), date_str


def load_universe_or_fallback(bhav_folder, fallback_path):
    """Universe priority: bhavcopies in repo  ->  live masters  ->  bundled list."""
    # 1) Authoritative: bhavcopy files committed to the repo
    try:
        m, date_str = build_universe_from_bhavcopies(bhav_folder)
        if m is not None:
            return m, []
    except Exception:  # noqa: BLE001
        pass

    # 2) Live exchange masters (often blocked from cloud hosts)
    notes = []
    nse = bse = None
    try:
        from nselib import capital_market
        e = capital_market.equity_list()
        e.columns = [c.strip() for c in e.columns]
        nse = pd.DataFrame({
            "name": e["NAME OF COMPANY"].astype(str).str.strip(),
            "nse_symbol": e["SYMBOL"].astype(str).str.strip(),
            "isin": e["ISIN NUMBER"].astype(str).str.strip()})
    except Exception:  # noqa: BLE001
        nse = None
    try:
        import bseindia
        b = bseindia.all_listed_securities()
        cols = list(b.columns)
        isin_c = _pick(cols, ["isin"])
        code_c = _pick(cols, ["securitycode", "scripcode", "code"])
        name_c = _pick(cols, ["securityname", "issuername", "name"])
        bse = pd.DataFrame({
            "name_b": b[name_c].astype(str).str.strip() if name_c else "",
            "bse_code": b[code_c].astype(str).str.strip() if code_c else None,
            "isin": b[isin_c].astype(str).str.strip() if isin_c else ""})
        bse = bse[bse["isin"].str.startswith("IN", na=False)]
    except Exception:  # noqa: BLE001
        bse = None

    if nse is not None or bse is not None:
        if nse is not None and bse is not None:
            m = pd.merge(nse, bse, on="isin", how="outer")
            m["name"] = m["name"].fillna(m["name_b"])
        elif nse is not None:
            m = nse.copy()
            m["bse_code"] = None
        else:
            m = bse.rename(columns={"name_b": "name"}).copy()
            m["nse_symbol"] = None
        m = (m[["name", "nse_symbol", "bse_code", "isin"]]
             .dropna(subset=["name"]).drop_duplicates("isin")
             .sort_values("name").reset_index(drop=True))
        return m, notes

    # 3) Last resort: small bundled list
    fb = pd.read_csv(fallback_path, dtype=str)
    for c in ("nse_symbol", "bse_code", "isin"):
        if c not in fb:
            fb[c] = None
    return fb[["name", "nse_symbol", "bse_code", "isin"]], [
        "Using the small bundled list — add bhavcopy files to the 'bhavcopies' "
        "folder in your repo for the full stock universe."]


# --------------------------------------------------------------------------- #
#  History
# --------------------------------------------------------------------------- #
def fetch_nse_history(symbol, start, end):
    if not symbol:
        return None
    try:
        from nselib import capital_market
        df = capital_market.price_volume_and_deliverable_position_data(
            symbol=str(symbol), from_date=start.strftime(DMY), to_date=end.strftime(DMY))
    except Exception as e:  # noqa: BLE001
        raise DataError(f"NSE: {type(e).__name__}: {e}") from e
    return df_to_ohlcv(df)


def fetch_bse_history(code, start, end):
    if not code or str(code).lower() in ("nan", "none", ""):
        return None
    try:
        from bseindia import equity
        df = equity.historical_stock_data(
            symbol=str(code), from_date=start.strftime(DMY), to_date=end.strftime(DMY))
    except Exception as e:  # noqa: BLE001
        raise DataError(f"BSE: {type(e).__name__}: {e}") from e
    return df_to_ohlcv(df)

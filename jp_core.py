"""Pure JP-footprint logic — no Streamlit, fully testable."""
import pandas as pd


def inr(n, d=2):
    if n is None or pd.isna(n):
        return "—"
    return "₹" + f"{n:,.{d}f}"


def indian_num(n):
    """Indian digit grouping for volumes, e.g. 25,98,864."""
    if n is None or pd.isna(n):
        return "—"
    n = int(round(n))
    neg = n < 0
    s = str(abs(n))
    if len(s) <= 3:
        out = s
    else:
        last3, rest, parts = s[-3:], s[:-3], []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        out = ",".join(parts) + "," + last3
    return ("-" if neg else "") + out


def is_jp(high):
    """True if the high ends in 9.90 or 9.95 (last rupee digit 9, paise 90/95)."""
    if high is None or pd.isna(high):
        return False
    c = int(round(high * 100))
    return (c % 100 in (90, 95)) and (c // 100 % 10 == 9)


def resample(df, rule):
    """Aggregate daily OHLCV into weekly / monthly candles."""
    if rule == "Daily":
        return df
    freq = "W-FRI" if rule == "Weekly" else "ME"
    return (df.set_index("Date").resample(freq)
            .agg(Open=("Open", "first"), High=("High", "max"),
                 Low=("Low", "min"), Close=("Close", "last"),
                 Volume=("Volume", "sum"))
            .dropna(subset=["Open"]).reset_index())


def analyse(df):
    """Return JP table, latest close, nearest above/below, and 3/5-day lows."""
    d = df.copy()
    d["is_jp"] = d["High"].apply(is_jp)
    jp = d[d["is_jp"]].copy()
    jp["above12"] = jp["High"] * 1.12
    jp["below12"] = jp["High"] * 0.88
    jp["oh"] = (jp["Open"].round(2) == jp["High"].round(2))
    jp["Year"] = jp["Date"].dt.year
    jp = jp.sort_values("Date", ascending=False)

    close = float(df.sort_values("Date")["Close"].iloc[-1])
    above = jp[jp["High"] > close].sort_values("High").head(1)
    below = jp[jp["High"] < close].sort_values("High", ascending=False).head(1)
    above = above.iloc[0] if len(above) else None
    below = below.iloc[0] if len(below) else None

    recent = df.sort_values("Date", ascending=False)
    return {"jp": jp, "close": close, "above": above, "below": below,
            "min3": recent["Low"].head(3).min(),
            "min5": recent["Low"].head(5).min()}

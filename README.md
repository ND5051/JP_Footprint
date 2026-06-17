# 👣 JP Footprint — NSE & BSE end-of-day dashboard

A personal stock dashboard. A **JP day** is any session whose **High ends in 9.90 or 9.95**
(e.g. 409.90, 469.95). For each JP day the app shows **+12% / −12%** off that high, finds the
**nearest JP above and below the latest close** (resistance / support), marks days where
**Open = High**, and shades the **3-day / 5-day lows**. Works on **Daily / Weekly / Monthly**.

---

## What's in the project

| File | What it is | Touch it? |
|---|---|---|
| `app.py` | The website itself (layout + display) | No |
| `jp_core.py` | The JP calculations | No |
| `data_sources.py` | Fetches data — NSE via `nselib`, BSE via `bseindia` (no account) | No |
| `bhavcopies/` | The two daily exchange files that build the full stock list | Replace to refresh |
| `fallback_instruments.csv` | Backup stock list, used only if the live lists can't be reached | Optional |
| `requirements.txt` | Tells the host which tools to install | No |
| `.streamlit/config.toml` | Hides the top-right toolbar / GitHub "Fork" button | No |
| `README.md` | This guide | — |

Keep them together (including the `.streamlit` folder) and upload as one group.

---

## Where the data comes from

Both feeds are by the same author (RuchiTanmay) and need **no account and no API key**:

- **NSE → `nselib`** — `price_volume_and_deliverable_position_data(symbol, from_date, to_date)`; deep history.
- **BSE → `bseindia`** — `historical_stock_data(code, from_date, to_date)`; deep history.

**The searchable stock list (universe)** is built from official **bhavcopy** files committed in the
`bhavcopies/` folder — one from NSE, one from BSE. They carry every listed equity plus its **ISIN**,
so the two exchanges are matched exactly (no guessing of BSE codes). With the included files that's
~5,000 stocks. If the folder is empty the app tries the live exchange lists, then a tiny built-in list.

### Refreshing the stock list (every few weeks is plenty — listings change slowly)
1. Download the latest **Equity bhavcopy (UDiFF / "full")** for a recent trading day from each exchange.
2. In your repo, open the **`bhavcopies`** folder → **Add file → Upload files** → drop in the two new
   files → **Commit changes**. (You can leave or delete the old ones; the app uses the newest by date.)
3. The app rebuilds the list automatically on its next load and shows the new date.

**Two things to know:**
1. **Cloud reachability is the real test.** NSE/BSE can block requests from non-Indian/datacenter
   IPs. If the dashboard loads but a panel never shows prices, that exchange is likely blocking the
   host. NSE blocks harder than BSE. The only way to know for sure is to deploy and look.
2. **`nselib`/`bseindia` need Python 3.10+** — set that in Streamlit's *Advanced settings* when deploying.

---

## Deploy it (no command line)

1. Create a free **GitHub** account, then a repository (e.g. `jp-footprint`).
2. Upload every file here, **keeping the `.streamlit/config.toml` inside a `.streamlit` folder**.
3. Make the repo **Private** if you want to keep the code to yourself (the free Streamlit tier
   allows one private repo). The included config already hides the "Fork"/GitHub button cosmetically.
4. Go to **share.streamlit.io**, sign in with GitHub, click **Create app**, pick your repo and `app.py`.
5. In **Advanced settings**, set **Python 3.11**. Click **Deploy**.

Your app gets a public URL you can share. Pushing changes to GitHub updates it automatically.

## Run it on your own computer

```
pip install -r requirements.txt
streamlit run app.py
```

---

## Notes

- **Consistent layout:** every box (price ladder, both nearest-JP cards, JP table, daily table)
  always renders — empty when there's no data — so the page looks identical for every stock.
- **Tables:** the JP table shows ~10 rows then scrolls; the daily table is fixed-height and scrolls.
- **Rate limits:** NSE/BSE rate-limit; the app caches each stock for the day. If one stock fails, retry shortly.
- **Fallback list:** if the live exchange lists can't be reached, a small bundled list is used so the
  app still opens. Its BSE codes are best-effort for large-caps only.
- **For research only — not investment advice.**

### Before charging users (later)
`nselib` is Apache-2.0. Confirm `bseindia`'s license on its repo, and that redistributing exchange
data commercially is within terms, before monetising. A licensed data feed is the clean long-term path.

# JP Footprint — your website, step by step

This guide takes you from **zero** to a **live website** anyone can open in a browser.
No coding and no command line — everything is done by clicking on websites.

**Total time:** ~15 minutes. **Cost:** ₹0.

You will do two things:
1. **GitHub** — a free place to store the app's files.
2. **Streamlit Community Cloud** — a free service that turns those files into a live website with a public link.

---

## The files in this folder

| File | What it is | Touch it? |
|---|---|---|
| `app.py` | The website itself | No (unless you want changes) |
| `jp_core.py` | The JP calculations | No |
| `requirements.txt` | Tells the host which tools to install | No |
| `fallback_instruments.csv` | Backup stock list (used only if the live lists are unreachable) | Optional |
| `README.md` | This guide | — |

Keep all five files together. You'll upload them as a group.

---

## Part A — Put the files on GitHub

**A1. Create a free GitHub account**
- Go to **https://github.com** → **Sign up**. Use your email, pick a username and password. Verify your email.

**A2. Create a new repository ("repo" = a folder for your project)**
- Click the **+** at the top-right → **New repository**.
- **Repository name:** `jp-footprint` (any name is fine).
- Set it to **Public** (required for the free Streamlit plan).
- Leave everything else as-is → click **Create repository**.

**A3. Upload the files**
- On the new repo page, click **“uploading an existing file”** (it's a blue link in the middle of the page). If you don't see it, click **Add file → Upload files**.
- Drag **all five files** from this folder into the box (or click **choose your files** and select them).
- Wait for them to finish uploading, then click the green **Commit changes** button at the bottom.

That's it — your code now lives on GitHub.

---

## Part B — Turn it into a live website

**B1. Create a free Streamlit account**
- Go to **https://share.streamlit.io**.
- Click **Continue with GitHub** and approve the access request. (Signing in with GitHub means the two services can talk to each other.)

**B2. Deploy your app**
- Click **Create app** (or **New app**).
- Choose **Deploy a public app from GitHub**.
- **Repository:** pick `your-username/jp-footprint`.
- **Branch:** `main`.
- **Main file path:** `app.py`.
- Click **Deploy**.

Streamlit now installs the tools and builds your site. The first build takes 2–5 minutes — that's normal. When it finishes you'll see your dashboard and a public URL like:

```
https://jp-footprint-yourname.streamlit.app
```

**Share that link with anyone.** Each visitor gets their own independent view; their selections never affect anyone else's.

---

## Using it

- **Stock:** click the box and start typing a company name.
- **Start date / Timeframe:** set the history start and switch between Daily / Weekly / Monthly.
- Dual-listed companies show **NSE (indigo)** and **BSE (amber)** side by side; single-listed companies show one.
- The first time a stock loads it takes a few seconds while data is fetched; after that it's cached for the day and instant.

---

## Changing things later (no command line)

1. Go to your repo on GitHub.
2. Click the file you want to edit (e.g. `app.py`) → click the **pencil ✏️** icon.
3. Make your change → **Commit changes**.
4. Your live site updates automatically within a minute.

To refresh the backup stock list, edit `fallback_instruments.csv` the same way.

---

## If something looks off

- **“No data returned” / a stock won't load:** usually Yahoo Finance is briefly rate-limiting. Wait a minute and reload. If one stock never works, its Yahoo symbol may differ — note it and we'll add a mapping.
- **Site shows “Zzz / wake app”:** on the free plan the site sleeps after a period of no visitors and takes ~30 seconds to wake. This is normal and disappears on a paid plan later.
- **A blue “fallback list” notice appears:** the live NSE/BSE lists couldn't be reached this minute; the app is running on the bundled backup list. It clears itself on the next refresh.

---

## Good to know for the future (monetization)

- **Data licensing:** Yahoo Finance data is free for personal/prototype use, but its terms restrict commercial redistribution. Before you **charge** users, plan to switch to a licensed data feed. The app is built so swapping the data source is a small change.
- **BSE-only stocks:** v1 covers the full NSE universe plus the BSE listing of any of those companies. Companies listed **only** on BSE (not on NSE) are a planned v2 addition via the BSE master list.
- **Accounts & payments:** when you're ready to monetize, the usual next steps are user logins, saved watchlists, and a paywall/subscription — each of which we can add in a later version.

When you're ready, tell me which direction you want to grow and we'll plan v2.

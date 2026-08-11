# Plot & Key — Property Marketplace

A Flask web app rebuilt from an original C++ OOP console project. Same domain
model (buyers, renters, owners, properties, listings, transactions, admin
approval, messaging, favorites) — now with a browser UI and data that
persists between runs.

## Run it locally

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000**

Admin panel: go to "Admin" in the nav, password is `admin123`.

## How it's organized

- `models.py` — the data classes (User/Buyer/Renter/Owner, Property, Listing,
  Transaction, Message). Direct translation of the original C++ classes.
- `store.py` — the `MarketPlace` class: holds everything in memory, saves/loads
  to `data.json` so your data survives a restart.
- `app.py` — Flask routes (the "controller" layer): registration, login,
  search, dashboards, buy/rent, admin approval.
- `templates/` — the HTML pages (Jinja2 templates).
- `static/style.css` — all styling.

## What changed from the C++ version (and why)

- **Fixed-size arrays → Python lists/dicts.** The original capped listings at
  100, favorites at 10, etc. Now there's no artificial ceiling.
- **Search returned only the first match → now returns all matches.** The
  original `searchByLocation`/`searchByPrice`/etc. had a `return` inside the
  loop, so it silently stopped after one hit.
- **Owner lookup via digit math → owner_id stored directly on Property.** The
  original reverse-engineered the owner's index from the property ID's first
  digit, which was fragile. Now it's just a direct reference.
- **No persistence → JSON file storage.** Data used to vanish when the C++
  program exited; now `data.json` keeps it between runs.
- **Admin approval wasn't wired up → now functional**, with pending/approve/
  reject all working end to end.

## Known simplifications (worth mentioning honestly if asked)

- Passwords are stored in plain text and there's no real session security —
  fine for a portfolio demo, not for handling real user data. A production
  version would use `werkzeug.security` password hashing and probably
  Flask-Login.
- JSON-file storage instead of a real database — fine for a demo, would move
  to SQLite/Postgres for anything real.
- No image uploads for properties yet.

These are good "what I'd add next" talking points for interviews — they show
you know the difference between a demo and a production system.

## Deploying it live (so you have a real URL for LinkedIn)

**Render** (free tier, easiest for Flask):
1. Push this folder to a GitHub repo.
2. Go to render.com → New → Web Service → connect your repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app` (add `gunicorn` to requirements.txt first)
5. Deploy — you'll get a live `https://yourapp.onrender.com` URL.

**Railway** works similarly and is also free-tier friendly.

Note: on most free hosting tiers, the filesystem resets on redeploy, so
`data.json` won't persist forever in production — that's expected and fine
for a portfolio demo. If you want it to persist for real, that's the point
where you'd swap in a proper database (a good "next step" to mention).

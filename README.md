# furigana.srt — web app

A small website that does what the local `srt_furigana.py` script does, but
through a browser: drop in `.srt` files, get back furigana-tagged copies,
no terminal required. Same word/phrase-level engine under the hood.

```
furigana-web/
├── app.py              Flask server (routes + file handling)
├── furigana_core.py    the furigana engine
├── templates/index.html
├── static/style.css
├── static/script.js
├── requirements.txt
├── Procfile             process command for Render/Heroku-style hosts
├── render.yaml           one-click config for Render
└── .gitignore
```

## 1. Run it locally first

```bash
cd furigana-web
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** — drop in an `.srt` file, click **Add
furigana**, it downloads the processed file. Multiple files download as a
zip automatically.

## 2. Put it online (Render.com, free tier)

Render is the easiest host for this: it runs any Python web service from a
GitHub repo, has a free tier, and needs no server config beyond what's
already in this folder (`render.yaml`, `requirements.txt`, `Procfile`).

**Step 1 — push this folder to GitHub**

```bash
cd furigana-web
git init
git add .
git commit -m "furigana web app"
```
Create a new empty repo on [github.com/new](https://github.com/new), then:
```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

**Step 2 — create the Render service**

1. Go to [render.com](https://render.com) and sign up / log in (GitHub
   login is easiest — it can read your repos directly).
2. Click **New** → **Web Service**.
3. Connect the GitHub repo you just pushed.
4. Render reads `render.yaml` automatically and fills in:
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --workers 2 --timeout 120`
   - Plan: Free
   If it asks you to confirm instead of auto-filling, just paste those same
   values in.
5. Click **Create Web Service**.

**Step 3 — wait for the first build**

The first deploy takes a few minutes — most of that time is downloading the
Japanese dictionary package (~75 MB). Render shows live build logs; once it
says "Your service is live", open the `.onrender.com` URL it gives you.
That's your website.

> **Free tier note:** Render's free web services spin down after ~15
> minutes of no traffic and take 30–60 seconds to wake back up on the next
> visit. That's fine for personal use; if you want it always-on, Render's
> cheapest paid tier (currently ~$7/mo) removes the spin-down.

**Updating the site later:** just commit and push again —
```bash
git add .
git commit -m "update"
git push
```
Render redeploys automatically on every push to `main`.

## Alternatives to Render

Any host that runs a standard Python web app works, since nothing here is
Render-specific beyond `render.yaml` (which is ignored elsewhere):
- **Railway** (railway.app) — similar flow, connect GitHub repo, it detects
  `Procfile` automatically.
- **Fly.io** — more setup (needs `fly launch` + a Dockerfile), but has a
  free allowance and no spin-down on their smallest always-on config.
- **PythonAnywhere** — good if you'd rather configure through a web
  dashboard instead of GitHub; Flask apps are a first-class case there.

## Notes

- Uploaded files are processed in memory and never written to disk — the
  server doesn't retain anything after it responds.
- `MAX_CONTENT_LENGTH` in `app.py` caps uploads at 25 MB total per request;
  raise it there if you need to batch a lot of large files at once.
- The dictionary loads once at server startup (`warm_up()` in `app.py`), so
  the first visitor after a cold start isn't stuck waiting on it — on
  Render's free tier that startup cost is instead paid once per spin-up
  after idling.

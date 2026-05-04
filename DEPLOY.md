# 🚀 Deploy FitBot AI to Render (Free)

## Step 1 — Push to GitHub

1. Go to [github.com](https://github.com) → Sign in or create account
2. Click **New Repository** → name it `fitbot-ai` → Public → **Create**
3. Open PowerShell in the project folder and run:

```powershell
git init
git add .
git commit -m "Initial commit - FitBot AI"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fitbot-ai.git
git push -u origin main
```

> Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 2 — Deploy on Render

1. Go to [render.com](https://render.com) → **Sign up** (free) with GitHub
2. Click **New +** → **Web Service**
3. Connect your GitHub → Select `fitbot-ai` repository
4. Fill in these settings:

| Setting | Value |
|---------|-------|
| **Name** | fitbot-ai |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free |

5. Click **Create Web Service**
6. Wait ~3-5 minutes for deployment
7. Your app will be live at: `https://fitbot-ai.onrender.com`

---

## Notes
- Free tier spins down after 15 min of inactivity (first request after idle takes ~30s to wake up)
- SQLite DB (`fitbot.db`) is ephemeral on Render free tier — data resets on redeploy
- For persistent DB, upgrade to Render Paid or use Render PostgreSQL

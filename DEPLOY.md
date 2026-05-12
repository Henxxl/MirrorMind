# 🚀 How to Deploy MirrorMind on Vercel

Follow these steps exactly.

---

## Step 1 — Put your files on GitHub

Vercel deploys from GitHub. You need to push the project there first.

1. Go to https://github.com and sign in (or create a free account)
2. Click the **"+"** button → **"New repository"**
3. Name it `mirrormind`, set it to **Public**, click **Create repository**
4. On your computer, open a terminal in the `PersonaLens` folder and run:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mirrormind.git
git push -u origin main
```

> Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 2 — Deploy to Vercel

1. Go to https://vercel.com and sign in with your GitHub account
2. Click **"Add New Project"**
3. Find and select your `mirrormind` repository
4. On the configuration screen:
   - **Framework Preset**: select `Other`
   - **Root Directory**: leave as `.` (the default)
   - **Build Command**: leave blank
   - **Output Directory**: type `frontend`
5. Click **Deploy**

---

## Step 3 — Add your Anthropic API Key

This is the most important step — without this, the AI won't work.

1. After deploying, go to your project on Vercel
2. Click **Settings** (top menu)
3. Click **Environment Variables** (left sidebar)
4. Click **Add New**:
   - **Name**: `ANTHROPIC_API_KEY`
   - **Value**: paste your actual API key (starts with `sk-ant-...`)
   - **Environment**: tick all three (Production, Preview, Development)
5. Click **Save**
6. Go to **Deployments** → click the three dots on your latest deployment → **Redeploy**

> Get your Anthropic API key at: https://console.anthropic.com/settings/keys

---

## Step 4 — Visit your live site

Your site will be live at: `https://mirrormind-[something].vercel.app`

The app works fully in the browser — the AI calls happen client-side using your API key.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Still seeing 404 | Make sure "Output Directory" is set to `frontend` in Vercel settings |
| AI not responding | Check your `ANTHROPIC_API_KEY` is set correctly in Environment Variables |
| API key error in console | Make sure the key starts with `sk-ant-` and has no spaces |
| Changes not showing | Go to Deployments → Redeploy |

---

## Local Development (no Vercel needed)

Just open `frontend/index.html` directly in your browser. It will call the Anthropic API directly from your browser — no server needed.

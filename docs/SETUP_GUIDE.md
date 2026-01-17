# FixionMail Setup Guide

This guide walks you through setting up FixionMail with Supabase on Railway for a small deployment (~10-50 users).

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│               Railway (Single Service)              │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │                 WEB SERVICE                   │  │
│  │  FastAPI + React Frontend                     │  │
│  │                                               │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │       APScheduler (In-Process)          │  │  │
│  │  │  • Story Worker (generates stories)     │  │  │
│  │  │  • Daily Scheduler (triggers at 8am)    │  │  │
│  │  │  • Delivery Worker (sends emails)       │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │       SUPABASE        │
              │  • Auth (magic links) │
              │  • PostgreSQL DB      │
              │  • File Storage       │
              └───────────────────────┘
```

**Why this architecture?**
- No Redis needed (saves $5-15/month)
- Single Railway service (saves $5-15/month)
- Simpler to maintain and debug
- Plenty of capacity for 10-50 daily users

---

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click **New Project**
3. Choose your organization
4. Set:
   - **Name**: `fixionmail` (or your preference)
   - **Database Password**: Generate a strong password (save it!)
   - **Region**: Choose closest to your users
5. Click **Create new project**
6. Wait for the project to initialize (~2 minutes)

### Get Your Credentials

Once created, go to **Settings > API** and note:

| Variable | Location |
|----------|----------|
| `SUPABASE_URL` | Project URL (https://xxxxx.supabase.co) |
| `SUPABASE_ANON_KEY` | Project API Keys > anon/public |
| `SUPABASE_SERVICE_KEY` | Project API Keys > service_role (keep secret!) |
| `SUPABASE_JWT_SECRET` | JWT Settings > JWT Secret |

---

## Step 2: Run Database Migrations

1. In Supabase Dashboard, click **SQL Editor** (left sidebar)
2. Click **New query**
3. Run these migrations in order:

### Option A: Quick Setup (Recommended)

Copy and run the contents of:
```
supabase/migrations/999_ensure_all_tables.sql
```

Then seed character names:
```
supabase/migrations/005_seed_character_names.sql
```

### Option B: Step by Step

Run each file in order:
1. `001_initial_schema.sql`
2. `002_add_story_jobs_table.sql`
3. `003_add_scheduled_deliveries.sql`
4. `004_add_character_names.sql`
5. `005_seed_character_names.sql`
6. `006_fix_duplicate_deliveries.sql`
7. `007_add_job_locking.sql`

### Verify Setup

Run the setup helper script locally:
```bash
# Set your credentials
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_KEY=your-service-key

# Run verification
python scripts/setup_supabase.py
```

---

## Step 3: Configure Supabase Auth

### Set Redirect URL

1. Go to **Authentication > URL Configuration**
2. Set **Site URL**: `https://your-app.up.railway.app`
3. Add to **Redirect URLs**:
   - `https://your-app.up.railway.app/auth/callback`
   - `http://localhost:5173/auth/callback` (for local dev)

### Enable Email Auth

1. Go to **Authentication > Providers**
2. Ensure **Email** is enabled
3. Configure email templates if desired (Authentication > Email Templates)

---

## Step 4: Set Up Railway

### Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click **New Project**
3. Choose **Deploy from GitHub repo**
4. Select your FixionMail repository
5. Railway will create a service automatically

### Configure the Service

1. Click on your service
2. Go to **Settings**:
   - **Name**: `fixionmail-web`
   - **Root Directory**: `/` (leave blank)
   - **Start Command**: `python start.py` (should auto-detect)

3. Go to **Variables** and add all environment variables from `.env.production.example`

### Required Variables

```bash
# Service Type
SERVICE_TYPE=web

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_KEY=eyJhbGci...
SUPABASE_JWT_SECRET=your-jwt-secret

# Workers (in-process)
ENABLE_STORY_WORKER=true
ENABLE_DAILY_SCHEDULER=true
ENABLE_DELIVERY_WORKER=true

# APIs
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
RESEND_API_KEY=re_...

# App Config
ENVIRONMENT=production
APP_BASE_URL=https://your-app.up.railway.app
PORT=8000
```

### Remove Unused Services

If you previously had separate worker/scheduler/delivery services:
1. Click each service
2. Go to **Settings > Danger Zone**
3. Click **Delete Service**

You only need the **web** service.

### Generate Domain

1. Click your service
2. Go to **Settings > Networking**
3. Click **Generate Domain**
4. Note your URL (e.g., `fixionmail-web.up.railway.app`)
5. Update `APP_BASE_URL` variable to match

---

## Step 5: Set Up External Services

### Resend (Email Delivery)

1. Go to [resend.com](https://resend.com) and sign up
2. **API Keys** > Create new key
3. Add to Railway: `RESEND_API_KEY=re_...`
4. **Domains** > Add your domain (or use their test domain)

### Stripe (Payments)

1. Go to [stripe.com](https://stripe.com) dashboard
2. **Developers > API keys** > Get your keys
3. Add to Railway:
   ```
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_PUBLISHABLE_KEY=pk_live_...
   ```
4. **Developers > Webhooks** > Add endpoint:
   - URL: `https://your-app.up.railway.app/api/stripe/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.*`, `invoice.*`
5. Get webhook signing secret: `STRIPE_WEBHOOK_SECRET=whsec_...`
6. Create products and get price IDs for subscription plans

### Anthropic (Claude AI)

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. **API Keys** > Create key
3. Add to Railway: `ANTHROPIC_API_KEY=sk-ant-...`

### OpenAI (Embeddings)

1. Go to [platform.openai.com](https://platform.openai.com)
2. **API Keys** > Create key
3. Add to Railway: `OPENAI_API_KEY=sk-...`

---

## Step 6: Deploy and Verify

1. Push your code to GitHub (if not already)
2. Railway will auto-deploy
3. Watch the deploy logs for errors
4. Once deployed, visit your URL

### Verify Checklist

- [ ] Homepage loads (React app)
- [ ] `/health` returns `{"status": "healthy"}`
- [ ] `/api/status` shows workers running
- [ ] Magic link login works
- [ ] Admin dashboard accessible at `/admin`

### Check Logs

In Railway, click **Deployments > View Logs** to see:
- Startup messages
- Worker status
- Any errors

You should see:
```
✓ Config loaded: True
✓ Supabase: Configured
🟢 Single-Process Mode (APScheduler)
✓ Background story worker started
✓ Daily story scheduler started
✓ Email delivery worker started
```

---

## Troubleshooting

### "Supabase: Not configured"

- Check `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set correctly
- Ensure no extra spaces or quotes in values

### Workers Not Starting

- Check `ENABLE_STORY_WORKER=true` (not `"true"`)
- Ensure `REDIS_URL` is NOT set (or empty)
- Check logs for import errors

### Email Not Sending

- Verify `RESEND_API_KEY` is correct
- Check Resend dashboard for delivery status
- Verify sender domain is configured

### Stories Not Generating

- Check `ANTHROPIC_API_KEY` is valid
- Look at `/admin` for job status
- Check logs for generation errors

---

## Scaling Up (50+ Users)

If you grow beyond 50 users, you can switch to Redis Queue mode:

1. Add Upstash Redis (Railway Add-ons or upstash.com)
2. Set `REDIS_URL=rediss://...`
3. Create separate services:
   - `SERVICE_TYPE=web` (web only)
   - `SERVICE_TYPE=worker` (job processing)
   - `SERVICE_TYPE=scheduler` (story scheduling)
   - `SERVICE_TYPE=delivery` (email delivery)

This provides better scalability and job persistence.

---

## Local Development

```bash
# Clone repo
git clone https://github.com/your-org/fixionmail.git
cd fixionmail

# Create .env from example
cp .env.example .env
# Edit .env with your Supabase credentials

# Install dependencies
pip install -r requirements.txt

# Run backend
python -m uvicorn backend.api.main:app --reload

# In another terminal, run frontend
cd frontend
npm install
npm run dev
```

---

## Support

- GitHub Issues: [your-repo/issues](https://github.com/your-org/fixionmail/issues)
- Check `/admin` dashboard for system status
- Review Railway logs for errors

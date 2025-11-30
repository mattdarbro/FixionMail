# Railway Deployment Guide

## Required Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Claude API for story generation |
| `OPENAI_API_KEY` | `sk-...` | TTS audio generation |
| `REPLICATE_API_TOKEN` | `r8_...` | Image generation (Imagen-3) |
| `RESEND_API_KEY` | `re_...` | Email delivery |
| `STORAGE_PATH` | `/app/storage` | Persistent storage path |
| `ENVIRONMENT` | `production` | Production mode |

## Optional Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `DATABASE_URL` | SQLite | PostgreSQL connection string if using Postgres |

---

## Setup Steps

### 1. Create Service
1. New Project in Railway
2. Deploy from GitHub repo
3. Railway auto-detects Python

### 2. Add Volume
1. Service → Settings → Volumes
2. Add volume mounted at `/app/storage`
3. This persists story data across deploys

### 3. Set Environment Variables
1. Service → Variables tab
2. Add each required variable
3. **No quotes around values**
4. **No spaces around `=`**

### 4. Deploy
Railway auto-deploys on variable changes. Check logs for:
```
✓ Config loaded: True
✓ Routes loaded: True
✓ Storage directory exists: /app/storage
```

---

## Troubleshooting

### Health Check Fails

**Check logs for:**
```
✗ Missing ANTHROPIC_API_KEY
```
→ Add the missing variable

```
Storage directory does not exist
```
→ Add volume at `/app/storage`

### API Key Errors

**Common mistakes:**
```bash
# Wrong - extra quotes
ANTHROPIC_API_KEY="sk-ant-..."

# Wrong - spaces
ANTHROPIC_API_KEY = sk-ant-...

# Right
ANTHROPIC_API_KEY=sk-ant-...
```

**Fix:** Delete the variable completely, re-add with exact value.

### Variable Not Working

1. Check spelling (case-sensitive)
2. Redeploy after changes
3. Check logs for what app sees

---

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Health check |
| `/dev` | Dev dashboard (HTML) |
| `/api/dev/onboarding` | Create story bible |
| `/api/dev/generate-story` | Generate story |

---

## Manual Health Check

```bash
curl https://your-app.railway.app/health
```

Expected:
```json
{"status": "healthy", "config_loaded": true, "routes_loaded": true}
```

---

## Rollback

If deployment breaks:
1. Deployments tab
2. Find previous working deploy (green check)
3. Click ⋯ → Redeploy

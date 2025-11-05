# Railway Environment Variables Setup

## Required Environment Variables

Your Story service in Railway needs these environment variables. Go to your service → **Variables** tab to add them.

### 🔴 Required (Application won't start without this)
```bash
OPENAI_API_KEY=sk-proj-...your-actual-key-here...
```
**Important**: Must start with `sk-` or `sk-proj-`. No quotes, no extra spaces.

### 🟡 Required for Production
```bash
ENVIRONMENT=production
```
**Important**: 
- Set this to `production` for Railway deployments
- ⚠️ **NO leading equals sign**: Just `ENVIRONMENT` (not `=ENVIRONMENT`)
- ⚠️ **NO spaces**: `ENVIRONMENT=production` (not `ENVIRONMENT = production`)
- The default is `development` (for local), but Railway needs `production`

### 🟡 Required for Data Persistence (ChromaDB + Session Checkpoints)
```bash
STORAGE_PATH=/app/storage
```
**Important**:
- Must be exactly `/app/storage` (matches your volume mount path)
- No trailing slash
- No quotes around the value
- This stores both ChromaDB vector data AND SQLite session checkpoints
- Without this, all session data will be lost on redeploy

### 🟢 Optional (for full functionality)
```bash
# Database (if using PostgreSQL instead of SQLite)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Media Generation
REPLICATE_API_TOKEN=r8_...your-token...
ELEVENLABS_API_KEY=sk_...your-key...

# Model Settings
IMAGE_MODEL=stability-ai/sdxl:latest

# LangSmith Tracing (optional)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=storyteller-app
```

## Common Errors

### "The environment value is incorrect or missing"

This usually means:

1. **OPENAI_API_KEY is missing or invalid**
   - ✅ Check: Service → Variables → Does `OPENAI_API_KEY` exist?
   - ✅ Check: Does it start with `sk-` or `sk-proj-`?
   - ✅ Check: No quotes around the value (Railway adds quotes automatically if needed)

2. **CHROMA_PERSIST_DIRECTORY format issue**
   - ✅ Check: Value is exactly `/app/storage` (no quotes, no trailing slash)
   - ✅ Check: Volume is mounted at `/app/storage`

3. **Extra spaces or quotes**
   - ❌ Wrong: `OPENAI_API_KEY="sk-..."`
   - ❌ Wrong: `OPENAI_API_KEY= sk-...`
   - ✅ Right: `OPENAI_API_KEY=sk-...`

## Verification Checklist

Before redeploying, verify:

- [ ] `OPENAI_API_KEY` is set and valid
- [ ] `STORAGE_PATH` is set to `/app/storage`
- [ ] Volume is mounted at `/app/storage` in your service (Settings → Volumes)
- [ ] No extra spaces or quotes in variable values
- [ ] All variables are in the **Story service** (not Postgres service)
- [ ] `ENVIRONMENT=production` is set for Railway deployments

## After Adding Variables

1. Click **Deploy** or wait for auto-deploy
2. Check the deployment logs for any errors
3. If you see "ValidationError" or "missing required field", check the variable name spelling (case-sensitive!)


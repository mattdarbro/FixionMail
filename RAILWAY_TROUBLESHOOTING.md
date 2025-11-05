# Railway Deployment Troubleshooting

## Health Check Failures

If your Railway deployment is failing health checks, follow these steps:

### 1. Check Deployment Logs

In Railway:
1. Go to your service
2. Click on the **Deployments** tab
3. Click on the failed deployment
4. Look at the **Deploy Logs** for error messages

### 2. Look for These Messages

**✅ Good Signs:**
```
✓ Config loaded: True
✓ Routes loaded: True
✓ Storage directory exists: /app/storage
✓ Storage writable: True
```

**❌ Problem Signs:**
```
⚠️  Config loading failed
⚠️  Routes loading failed
⚠️  WARNING: Config failed to load
✗ Missing ANTHROPIC_API_KEY
⚠️  Storage directory does not exist
```

### 3. Common Issues and Fixes

#### Issue: `ANTHROPIC_API_KEY: ✗ Missing`
**Fix:**
1. Go to Service → **Variables**
2. Add `ANTHROPIC_API_KEY` with your Anthropic API key
3. Make sure there are no quotes or extra spaces
4. Redeploy

#### Issue: `Storage directory does not exist: /app/storage`
**Fix:**
1. Go to Service → **Settings** → **Volumes**
2. Make sure you have a volume mounted at `/app/storage`
3. If not, create a new volume and mount it at `/app/storage`
4. Redeploy

#### Issue: `STORAGE_PATH: ✗ Not set`
**Fix:**
1. Go to Service → **Variables**
2. Add `STORAGE_PATH=/app/storage` (no quotes, no trailing slash)
3. Redeploy

#### Issue: Health check times out after 300 seconds
**Possible causes:**
- App is crashing during startup
- Port binding issue (app not listening on $PORT)
- Database initialization taking too long

**Fix:**
1. Check the logs for Python errors or stack traces
2. Verify `PORT` environment variable is being used by gunicorn
3. Try adding more memory to your service (Settings → Resources)

### 4. Manual Health Check Test

After deployment, try hitting the health endpoint manually:

```bash
curl https://your-app.railway.app/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "config_loaded": true,
  "routes_loaded": true
}
```

If `config_loaded` or `routes_loaded` is `false`, check the deployment logs for detailed error messages.

### 5. Required Environment Variables Checklist

- [ ] `ANTHROPIC_API_KEY` - Your Anthropic API key (starts with `sk-ant-`)
- [ ] `STORAGE_PATH=/app/storage` - Path to persistent volume
- [ ] Volume mounted at `/app/storage` in Service Settings
- [ ] `ENVIRONMENT=production` (optional but recommended)

### 6. Still Not Working?

If health checks still fail:

1. **Check Railway Status**: https://status.railway.app
2. **Check your plan**: Free tier has limitations
3. **Try a manual deploy**: Sometimes Railway needs a fresh deploy
4. **Check build logs**: Make sure all dependencies installed correctly
5. **Verify Python version**: Railway should auto-detect from runtime.txt

### 7. Emergency Rollback

If you need to rollback to a working deployment:

1. Go to **Deployments** tab
2. Find a previous working deployment (green checkmark)
3. Click the **⋯** menu on that deployment
4. Click **Redeploy**

## Debugging Tips

### View Live Logs

```bash
# Watch logs in real-time from Railway CLI
railway logs
```

### Check if App is Running

```bash
# Test root endpoint
curl https://your-app.railway.app/

# Should return API info if working
```

### Verify Environment Variables

Check the startup logs for:
```
🔍 Environment Check:
   ANTHROPIC_API_KEY: ✓ Set
   STORAGE_PATH: /app/storage
   PORT: 8000
   ENVIRONMENT: production
```

## Need More Help?

1. Check Railway docs: https://docs.railway.app
2. Share your deployment logs (remove any API keys first!)
3. Verify all environment variables are set correctly

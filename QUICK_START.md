# Quick Start Guide

## 🚀 Starting the Backend (Easiest Way)

### Option 1: Use the Startup Script (Recommended)

```bash
./start_backend.sh
```

This script will:
- ✅ Check for `.env` file (create from example if missing)
- ✅ Create virtual environment if needed
- ✅ Install all dependencies
- ✅ Create necessary directories
- ✅ Start the backend server

### Option 2: Manual Setup

If you prefer manual control:

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Copy environment file
cp .env.example .env
# Edit .env with your API keys

# 5. Start server
cd backend
python -m uvicorn api.main:app --reload
```

## 🔑 Required API Keys

Before starting, you need:

1. **ANTHROPIC_API_KEY** - Get from https://console.anthropic.com
2. **OPENAI_API_KEY** - Get from https://platform.openai.com

Optional (for full features):
3. **ELEVENLABS_API_KEY** - Get from https://elevenlabs.io
4. **REPLICATE_API_TOKEN** - Get from https://replicate.com

Add these to your `.env` file.

## 🧪 Test the Backend

Once running, visit:
- **API**: http://127.0.0.1:8000
- **Interactive Docs**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health (if available)

Try starting a story:
```bash
curl -X POST http://localhost:8000/story/start \
  -H "Content-Type: application/json" \
  -d '{"world_id": "west_haven"}'
```

## ❌ Common Issues

### "Python not found"
**Solution**: Install Python 3.11+
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# Windows
# Download from python.org
```

### "Module not found" errors
**Solution**: Install dependencies
```bash
source venv/bin/activate  # Activate venv first!
pip install -r backend/requirements.txt
```

### "Permission denied: ./start_backend.sh"
**Solution**: Make script executable
```bash
chmod +x start_backend.sh
```

### "Port 8000 already in use"
**Solution**: Kill existing process or use different port
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
cd backend
python -m uvicorn api.main:app --reload --port 8001
```

### "API key not set" errors
**Solution**: Check your `.env` file
```bash
# Make sure .env exists
cat .env

# Should contain:
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

## 📱 Testing with Frontend

If you want to test with the frontend:

```bash
# Terminal 1: Backend
./start_backend.sh

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173

## 🐛 Debugging

Enable debug logs:
```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

Check backend logs for errors - they'll show:
- API key issues
- Missing dependencies
- Generation errors
- Cost tracking

## 💰 Cost Monitoring

Each 2500-word chapter costs ~$0.80:
- Claude: $0.05
- ElevenLabs: $0.75

Monitor your usage:
- Anthropic: https://console.anthropic.com/settings/usage
- ElevenLabs: https://elevenlabs.io/app/usage

## 🔄 Updating Code

When you pull new changes:
```bash
# Update dependencies
source venv/bin/activate
pip install -r backend/requirements.txt --upgrade

# Restart backend
# Ctrl+C to stop, then ./start_backend.sh again
```

## 📚 Next Steps

1. ✅ Start backend (you're here!)
2. ⏭️ Test 2500-word chapter generation (see TESTING_GUIDE.md)
3. ⏭️ Set up Resend email service (see docs/RESEND_SETUP.md)
4. ⏭️ Deploy to Railway (environment variables)

## 🆘 Still Having Issues?

1. Check Python version: `python3 --version` (should be 3.11+)
2. Check virtual environment is activated: `which python` (should show venv path)
3. Check all dependencies installed: `pip list | grep langchain`
4. Check .env file exists and has keys: `cat .env`
5. Check backend logs for specific errors

If all else fails, try clean install:
```bash
rm -rf venv
./start_backend.sh
```

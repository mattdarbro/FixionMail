# Testing Guide: 2500-Word Chapter Generation

## 🎯 Goal
Test the new 2500-word chapter system with 30-chapter tracking.

## 📋 Prerequisites

### 1. API Keys Required
```bash
# Copy example and fill in your keys
cp .env.example .env

# Edit .env with your actual keys:
# - ANTHROPIC_API_KEY (required)
# - OPENAI_API_KEY (required)
# - ELEVENLABS_API_KEY (required for audio)
# - REPLICATE_API_TOKEN (optional for images)
```

### 2. Install Dependencies
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend (optional for dev testing)
cd ../frontend
npm install
```

## 🧪 Test 1: Generate First Chapter (Local)

### Start Backend
```bash
cd backend
python -m uvicorn api.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Start Frontend (Optional)
```bash
cd frontend
npm run dev
```

### Test via API (Recommended)

**Option A: Using curl**
```bash
# Start a new story
curl -X POST http://localhost:8000/story/start \
  -H "Content-Type: application/json" \
  -d '{"world_id": "west_haven"}'
```

**Option B: Using Python**
```python
import requests
import json

# Start story
response = requests.post('http://localhost:8000/story/start',
    json={'world_id': 'west_haven'})

data = response.json()
print(f"Session ID: {data['session_id']}")
print(f"Chapter: {data['current_beat']}")
print(f"Word count: {len(data['narrative'].split())}")
print(f"\nNarrative:\n{data['narrative'][:500]}...")
print(f"\nChoices: {len(data['choices'])}")
for choice in data['choices']:
    print(f"  {choice['id']}: {choice['text'][:50]}...")
```

**Option C: Using Frontend**
1. Open http://localhost:5173
2. Click "Start Story"
3. Select "West Haven"
4. Read through Chapter 1

## 📊 What to Check

### ✅ Chapter Generation
- [ ] Chapter is ~2500 words (not 300)
- [ ] Generation takes ~30-60 seconds (longer than before)
- [ ] Narrative is coherent and well-structured
- [ ] Chapter shows "Chapter 1 of 30" in logs

### ✅ Audio Generation
- [ ] Audio file is generated
- [ ] Audio is ~10-15 minutes long (vs 1-2 min before)
- [ ] Audio URL is returned in response
- [ ] ElevenLabs usage increases (~$0.75 per chapter)

### ✅ Image Generation (Optional)
- [ ] Image is generated
- [ ] Image matches chapter scene
- [ ] Image URL is returned

### ✅ State Tracking
Check backend logs for:
```
✓ Generating opening narrative for beat 1
✓ Chapter 1 complete. Starting Chapter 2/30 (7%)
```

### ✅ Story Progress
- [ ] `chapter_number` increments (1 → 2)
- [ ] `story_progress_pct` shows correct % (3.3% → 6.7%)
- [ ] Choices lead to Chapter 2

## 🐛 Common Issues

### Issue: "MAX_TOKENS too low"
**Symptom**: Chapter cuts off mid-sentence
**Fix**: Check `.env` has `MAX_TOKENS=4000`

### Issue: "Generation times out"
**Symptom**: Request fails after 2 minutes
**Fix**:
1. Increase timeout in `config.py` if needed
2. Consider using Claude Haiku (faster) for dev testing

### Issue: "ElevenLabs quota exceeded"
**Symptom**: Audio generation fails with 429 error
**Fix**:
1. Check ElevenLabs dashboard for quota
2. Temporarily disable audio: `ENABLE_MEDIA_GENERATION=false`

### Issue: "Chapter is still ~300 words"
**Symptom**: Short chapters despite config change
**Fix**:
1. Restart backend (config may be cached)
2. Check `.env` is being loaded: `python -c "from backend.config import config; print(config.MAX_TOKENS)"`

## 📈 Cost Monitoring

Track costs during testing:

**Claude (Anthropic):**
- Check usage: https://console.anthropic.com/settings/usage
- Expected: ~$0.05 per 2500-word chapter

**ElevenLabs:**
- Check usage: https://elevenlabs.io/app/usage
- Expected: ~$0.75 per 2500-word chapter

**Total per chapter: ~$0.80**

## 🎉 Success Criteria

✅ **Chapter 1 generated successfully**
- ~2500 words
- Coherent narrative
- 3 choices for Chapter 2
- Audio generated (~10-15 min)
- Progress shows "Chapter 1 of 30"

✅ **Chapter 2 generated from choice**
```bash
# Continue story
curl -X POST http://localhost:8000/story/continue \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SESSION_ID_HERE", "choice_id": 1}'
```

- Flows naturally from Chapter 1
- Progress shows "Chapter 2 of 30 (7%)"
- Story bible updates correctly

## 🚀 Next Steps After Testing

Once local testing works:

1. **Deploy to Railway** with updated env vars
2. **Set up Resend** for email delivery
3. **Add media storage** (Cloudflare R2)
4. **Implement async job queue**
5. **Create email templates**

## 📝 Report Issues

If you encounter issues, check:
1. Backend logs (`uvicorn` output)
2. Frontend console (F12 in browser)
3. API response JSON
4. File sizes in `generated_audio/` and `generated_images/`

Share relevant logs for debugging!

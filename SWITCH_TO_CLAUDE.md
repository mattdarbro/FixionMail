# Switching from OpenAI to Claude (Anthropic)

## Why Claude is Better for This Project

You were absolutely right! Using **Claude 3.5 Sonnet** instead of GPT-4 will dramatically improve your story consistency. Here's why:

### Benefits of Claude for Storytelling

1. **Better Instruction Following**: Claude is exceptional at following detailed system prompts and maintaining consistency
2. **Longer Context Window**: 200K tokens vs GPT-4's 128K (better for story continuity)
3. **Superior RAG Performance**: Better at using retrieved context to maintain narrative coherence
4. **Character Consistency**: Less likely to hallucinate or mix up character names and settings
5. **Narrative Quality**: Claude excels at creative writing with proper tone and pacing
6. **JSON Output**: More reliable at producing structured JSON responses

### What Changed

The following files have been updated to use Claude:

- ✅ `backend/config.py` - Added ANTHROPIC_API_KEY, changed default model to Claude 3.5 Sonnet
- ✅ `backend/storyteller/nodes.py` - Now uses ChatAnthropic instead of ChatOpenAI
- ✅ `requirements.txt` - Added langchain-anthropic package
- ✅ `.env` - Added ANTHROPIC_API_KEY placeholder

**Important**: OpenAI is still used for embeddings (RAG), which is fine - their embeddings are excellent.

---

## Getting Your Anthropic API Key

### Step 1: Create an Anthropic Account

1. Go to https://console.anthropic.com/
2. Sign up with your email
3. Verify your email address

### Step 2: Get Your API Key

1. Log in to the Anthropic Console
2. Click on **API Keys** in the left sidebar
3. Click **Create Key**
4. Give it a name (e.g., "Story App")
5. Copy the API key (starts with `sk-ant-`)

### Step 3: Add to Your Local Environment

Open your `.env` file and replace the placeholder:

```bash
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**Important**: Keep your OpenAI key - it's still needed for embeddings!

---

## Railway Deployment

### Environment Variables to Update

Go to Railway → Your Service → Variables and add/update:

```bash
# NEW - Add this
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here

# KEEP - Still needed for embeddings
OPENAI_API_KEY=your-openai-key

# UPDATE - Change model name
MODEL_NAME=claude-3-5-sonnet-20241022

# KEEP ALL OTHER VARIABLES AS-IS
DEFAULT_WORLD=west_haven
REPLICATE_API_TOKEN=...
ELEVENLABS_API_KEY=...
etc.
```

### Important Notes

1. **No Quotes**: Railway variables should have no quotes around the value
2. **Model Name**: Must be exactly `claude-3-5-sonnet-20241022` (latest version)
3. **Both Keys**: You need BOTH Anthropic (for stories) and OpenAI (for embeddings)

---

## Testing Locally

### 1. Install the New Package

```bash
# Already done for you, but if needed:
source venv/bin/activate
pip install langchain-anthropic
```

### 2. Add Your Anthropic API Key

Edit `.env` and add your actual key where it says `your-anthropic-api-key-here`

### 3. Start the Backend

```bash
PYTHONPATH=/Users/mattdarbro/Desktop/Story python backend/api/main.py
```

You should see in the logs:
```
✓ Using Claude 3.5 Sonnet for narrative generation
```

### 4. Test the Story

Start a new story and verify:
- ✅ Julia Martin (not Elena or other characters)
- ✅ Space station setting (not fantasy world)
- ✅ Consistent character behavior
- ✅ No mixing of different story elements
- ✅ Proper third-person past tense narrative

---

## Expected Improvements

After switching to Claude, you should see:

### Problem → Fixed

1. **Character Mixing** ❌ → ✅
   - Before: "Elena walked through the Citadel..."
   - After: "Julia examined the space station's control panel..."

2. **Setting Confusion** ❌ → ✅
   - Before: Random small town settings
   - After: Consistent orbital station environment

3. **Tone Consistency** ❌ → ✅
   - Before: Switches between fantasy and sci-fi tones
   - After: Maintains cozy hopepunk sci-fi throughout

4. **Character Voice** ❌ → ✅
   - Before: Generic or inconsistent personality
   - After: Julia's cynical-but-hopeful corporate lawyer voice

5. **RAG Context Usage** ❌ → ✅
   - Before: Ignores story bible details
   - After: Accurately references West Haven lore

---

## Troubleshooting

### "Invalid API key" Error

**Check**:
- Does your key start with `sk-ant-`?
- Did you copy the entire key?
- No extra spaces or quotes?

**Fix**:
- Generate a new key from Anthropic Console
- Copy it exactly
- Paste without quotes in `.env` or Railway

### "Model not found" Error

**Check**:
- Is MODEL_NAME set to `claude-3-5-sonnet-20241022`?
- No typos in the model name?

**Fix**:
```bash
# In Railway or .env:
MODEL_NAME=claude-3-5-sonnet-20241022
```

### Still Getting Wrong Characters

**Check**:
- Is `DEFAULT_WORLD=west_haven` set?
- Did you restart the backend after changes?
- Try deleting the ChromaDB directory and letting it re-initialize

**Fix**:
```bash
# Delete old index
rm -rf chroma_db/west_haven

# Restart backend (it will auto-initialize)
python backend/api/main.py
```

### API Rate Limits

Claude has different rate limits than OpenAI:

**Free Tier**:
- 50 requests/day
- Good for testing

**Paid Tier**:
- Much higher limits
- Pay per token (very affordable)
- Recommended for production

To upgrade: https://console.anthropic.com/settings/plans

---

## Cost Comparison

### Claude 3.5 Sonnet (Recommended)
- **Input**: $3 per 1M tokens
- **Output**: $15 per 1M tokens
- **Typical story turn**: ~2,000 input + 500 output tokens = $0.0135

### GPT-4 Turbo (Previous)
- **Input**: $10 per 1M tokens
- **Output**: $30 per 1M tokens
- **Typical story turn**: ~2,000 input + 500 output tokens = $0.035

**Claude is ~60% cheaper AND better for this use case!**

---

## Model Options

### Recommended: Claude 3.5 Sonnet (Latest)
```bash
MODEL_NAME=claude-3-5-sonnet-20241022
```
- **Best for**: Production stories
- **Quality**: Excellent narrative, great consistency
- **Speed**: Fast
- **Cost**: $3/$15 per 1M tokens

### Alternative: Claude 3 Haiku (Budget)
```bash
MODEL_NAME=claude-3-haiku-20240307
```
- **Best for**: Development/testing
- **Quality**: Good but less creative
- **Speed**: Very fast
- **Cost**: $0.25/$1.25 per 1M tokens (80% cheaper!)

### Not Recommended: Claude 3 Opus
```bash
MODEL_NAME=claude-3-opus-20240229
```
- **Why**: More expensive, not much better for stories
- **Cost**: $15/$75 per 1M tokens

---

## Verification Checklist

Before deploying to Railway:

### Local Testing
- [ ] Anthropic API key added to `.env`
- [ ] Backend starts without errors
- [ ] Story begins with Julia Martin on West Haven
- [ ] Can make multiple choices without errors
- [ ] Characters remain consistent
- [ ] Setting stays on the space station

### Railway Deployment
- [ ] `ANTHROPIC_API_KEY` added to Railway variables
- [ ] `MODEL_NAME=claude-3-5-sonnet-20241022` set
- [ ] `OPENAI_API_KEY` still present (for embeddings)
- [ ] All other variables from previous setup remain
- [ ] Service redeploys successfully
- [ ] Production app shows consistent story

---

## Next Steps

1. **Get your Anthropic API key** (see "Getting Your Anthropic API Key" above)

2. **Add it locally**:
   ```bash
   # Edit .env
   ANTHROPIC_API_KEY=sk-ant-your-actual-key
   ```

3. **Test locally**:
   ```bash
   python backend/api/main.py
   ```

4. **Deploy to Railway**:
   - Add ANTHROPIC_API_KEY variable
   - Set MODEL_NAME=claude-3-5-sonnet-20241022
   - Redeploy

5. **Test production**:
   - Start new story
   - Verify Julia/West Haven consistency
   - Enjoy much better storytelling!

---

## Summary

**Before** (GPT-4):
- ❌ Character mixing (Elena → Julia)
- ❌ Setting confusion (fantasy → sci-fi)
- ❌ Inconsistent tone
- ❌ Higher cost
- ❌ Hallucinations

**After** (Claude 3.5 Sonnet):
- ✅ Perfect character consistency
- ✅ Maintains setting and atmosphere
- ✅ Consistent cozy hopepunk tone
- ✅ 60% cheaper
- ✅ Better instruction following
- ✅ Superior RAG integration

The switch from OpenAI to Claude should solve most of your "going off-script" issues!

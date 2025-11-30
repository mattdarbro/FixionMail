# Available Models and Voices

## Image Generation (Replicate)

Currently using **Google Imagen-3 Fast** via Replicate.

| Model | Cost | Speed | Quality |
|-------|------|-------|---------|
| Imagen-3 Fast | ~$0.02 | Fast | Excellent |

---

## TTS Voices (OpenAI)

All voices use OpenAI's TTS API.

| Voice | Feel | Best For |
|-------|------|----------|
| **alloy** | Neutral & Balanced | Any genre |
| **echo** | Warm & Thoughtful | Drama, Noir |
| **fable** | British & Expressive | Fantasy, Literary |
| **onyx** | Deep & Authoritative | Thriller, Mystery |
| **nova** | Friendly & Bright | Romance, Light Fiction |
| **shimmer** | Soft & Gentle | Emotional, Intimate |

### Cost
- ~$0.015 per 1000 characters
- ~$0.02-0.04 per story (1500-3000 words)

---

## AI Models (Anthropic Claude)

### Story Generation

| Model | Use | Cost (per 1M tokens) |
|-------|-----|---------------------|
| **Claude Sonnet 4.5** | Writer (default) | $3 in / $15 out |
| **Claude Opus 4.5** | Writer (premium) | $5 in / $25 out |
| **Claude Haiku 4.5** | Judge | $1 in / $5 out |

### Model Selection
- **Sonnet**: Fast, high-quality writing (default)
- **Opus**: Premium quality, deeper creativity (optional)

Select in the dev dashboard before generating.

---

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...    # Claude (story generation)
OPENAI_API_KEY=sk-...           # TTS only
REPLICATE_API_TOKEN=r8_...      # Image generation
```

### Voice Selection
Voice is selected per-story in the dashboard UI.

---

## Cost Summary (Per Story)

| Component | Sonnet | Opus |
|-----------|--------|------|
| Story (Writer + Judge) | ~$0.03-0.06 | ~$0.08-0.15 |
| Image | ~$0.02 | ~$0.02 |
| Audio | ~$0.02-0.04 | ~$0.02-0.04 |
| **Total** | **~$0.07-0.12** | **~$0.12-0.21** |

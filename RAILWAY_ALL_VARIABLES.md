# Complete Railway Environment Variables List

## 🔴 Required (Minimum to Run)

These are the **essential** variables needed for the app to work:

1. **`OPENAI_API_KEY`** (Required for API to function)
   - Value: `sk-proj-...` or `sk-...`
   - Purpose: Used for story generation and RAG embeddings

2. **`ENVIRONMENT`** (Required for production)
   - Value: `production`
   - Purpose: Sets production mode

3. **`Storage_Path`** (Required for ChromaDB and session persistence)
   - Value: `/app/storage`
   - Purpose: Where ChromaDB stores vector data and SQLite checkpoint database
   - Note: This is the alias for `CHROMA_PERSIST_DIRECTORY`
   - Important: Also used for storing `story_checkpoints.db` (session persistence)

---

## 🟡 Recommended (For Full Functionality)

4. **`DATABASE_URL`** (If using PostgreSQL from Railway)
   - Value: `postgresql://user:pass@host:5432/dbname`
   - Purpose: Database for session persistence
   - Default: Uses SQLite (file-based, less reliable in production)

5. **`REPLICATE_API_TOKEN`** (For image generation)
   - Value: `r8_...`
   - Purpose: Generate story images
   - Note: Optional, but needed for image generation

6. **`ELEVENLABS_API_KEY`** (For audio generation)
   - Value: `sk_...`
   - Purpose: Generate voice narration
   - Note: Optional, but needed for audio generation

---

## 🟢 Optional (Credits & Advanced)

7. **`CREDITS_PER_NEW_USER`** (Optional - defaults to 25)
   - Value: `25` (or any number)
   - Purpose: Starting credits for new users
   - Note: Only matters if `ENABLE_CREDIT_SYSTEM=true`

8. **`CREDITS_PER_CHOICE`** (Optional - defaults to 1)
   - Value: `1` (or any number)
   - Purpose: Credits deducted per story choice
   - Note: Only matters if `ENABLE_CREDIT_SYSTEM=true`

9. **`ENABLE_CREDIT_SYSTEM`** (Optional - defaults to false)
   - Value: `true` or `false`
   - Purpose: Enable credit tracking and limits
   - Default: `false` (disabled)

---

## 🔵 Advanced/Optional (Tuning & Debugging)

10. **`MODEL_NAME`** (Optional - defaults to `gpt-4-turbo-preview`)
    - Value: `gpt-4-turbo-preview`, `gpt-4`, etc.
    - Purpose: Which OpenAI model to use

11. **`EMBEDDING_MODEL`** (Optional - defaults to `text-embedding-3-small`)
    - Value: `text-embedding-3-small`, `text-embedding-3-large`, etc.
    - Purpose: Embedding model for RAG

12. **`TEMPERATURE`** (Optional - defaults to `0.7`)
    - Value: `0.0` to `2.0`
    - Purpose: Creativity level (lower = more consistent, higher = more creative)

13. **`MAX_TOKENS`** (Optional - defaults to `1000`)
    - Value: `100` to `4000`
    - Purpose: Maximum tokens per LLM response

14. **`ENABLE_MEDIA_GENERATION`** (Optional - defaults to `true`)
    - Value: `true` or `false`
    - Purpose: Enable/disable image and audio generation
    - Note: If false, images/audio won't generate even with API keys

15. **`RAG_RETRIEVAL_K`** (Optional - defaults to `6`)
    - Value: `1` to `20`
    - Purpose: Number of documents to retrieve for RAG

16. **`RAG_FETCH_K`** (Optional - defaults to `20`)
    - Value: `1` to `100`
    - Purpose: Number of documents to fetch before filtering

17. **`RAG_SEARCH_TYPE`** (Optional - defaults to `mmr`)
    - Value: `mmr` or `similarity`
    - Purpose: RAG search algorithm

18. **`DEFAULT_WORLD`** (Optional - defaults to `tfogwf`)
    - Value: `tfogwf`, `west_haven`, `focused_story`
    - Purpose: Default story world

19. **`LOG_LEVEL`** (Optional - defaults to `INFO`)
    - Value: `DEBUG`, `INFO`, `WARNING`, `ERROR`
    - Purpose: Logging verbosity

20. **`LANGCHAIN_TRACING_V2`** (Optional - defaults to `false`)
    - Value: `true` or `false`
    - Purpose: Enable LangSmith tracing for debugging

21. **`LANGCHAIN_API_KEY`** (Optional)
    - Value: Your LangSmith API key
    - Purpose: Required if `LANGCHAIN_TRACING_V2=true`

22. **`LANGCHAIN_PROJECT`** (Optional - defaults to `storyteller-app`)
    - Value: Project name in LangSmith
    - Purpose: Groups traces in LangSmith

---

## 📋 Quick Setup Checklist

### Minimum (3 variables - app runs):
- [ ] `OPENAI_API_KEY`
- [ ] `ENVIRONMENT=production`
- [ ] `Storage_Path=/app/storage`

### Recommended (5-6 variables - full functionality):
- [ ] `OPENAI_API_KEY`
- [ ] `ENVIRONMENT=production`
- [ ] `Storage_Path=/app/storage`
- [ ] `DATABASE_URL` (if using Postgres)
- [ ] `REPLICATE_API_TOKEN` (if you want images)
- [ ] `ELEVENLABS_API_KEY` (if you want audio)

### With Credits (8-9 variables):
- [ ] All from "Recommended" above
- [ ] `ENABLE_CREDIT_SYSTEM=true`
- [ ] `CREDITS_PER_NEW_USER=25`
- [ ] `CREDITS_PER_CHOICE=1`

---

## 💡 Notes

- **Most variables have sensible defaults** - you only need to set them if you want to change the default behavior
- **Credits system is disabled by default** - set `ENABLE_CREDIT_SYSTEM=true` to enable it
- **Storage_Path vs CHROMA_PERSIST_DIRECTORY** - Use `Storage_Path` (it takes precedence)
- **All variables are case-sensitive** - Make sure capitalization matches exactly

---

## Your Current Setup (9 variables)

Based on what you mentioned, you likely have:
1. `OPENAI_API_KEY`
2. `ENVIRONMENT`
3. `Storage_Path`
4. Possibly `REPLICATE_API_TOKEN`
5. Possibly `ELEVENLABS_API_KEY`
6. Possibly `CREDITS_PER_NEW_USER`
7. Possibly `CREDITS_PER_CHOICE`
8. Possibly `ENABLE_CREDIT_SYSTEM`
9. Possibly `DATABASE_URL`

You can check in Railway → Your Service → Variables tab to see what you have set!


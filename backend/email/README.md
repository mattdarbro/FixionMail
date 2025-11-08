# Email Scheduler System

Email delivery system for StoryKeeper using Resend API. Sends chapter emails to users at scheduled times.

## Features

- ✅ Send chapter emails with audio player and choice buttons
- ✅ Schedule emails for future delivery (default: tomorrow 8 AM)
- ✅ Immediate delivery in dev mode for testing
- ✅ Background processor runs every minute
- ✅ SQLite database for tracking scheduled emails
- ✅ Welcome email when user signs up (optional)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `resend` - Email API client
- `apscheduler` - Background task scheduler

### 2. Get Resend API Key

1. Go to [resend.com](https://resend.com)
2. Sign up (free tier available)
3. Navigate to **API Keys** → **Create API Key**
4. Copy the key (starts with `re_`)

### 3. Configure Environment Variables

Add to your `.env` file:

```bash
# Required
RESEND_API_KEY=re_xxxxxxxxxxxxx

# Optional (with defaults)
EMAIL_DB_PATH=email_scheduler.db
EMAIL_DEV_MODE=true  # true = send immediately, false = schedule for tomorrow
SEND_WELCOME_EMAIL=false  # true = send welcome email on signup
ENABLE_EMAIL_SCHEDULER=true  # true = run background processor
```

## How It Works

### Flow Diagram

```
User Signs Up
    ↓
    [Optional] Welcome email sent immediately
    ↓
User Makes Choice
    ↓
    ┌─────────────────────────────────────┐
    │ EMAIL_DEV_MODE=true (Dev)           │
    │ → Send chapter immediately          │
    │                                     │
    │ EMAIL_DEV_MODE=false (Production)   │
    │ → Schedule for tomorrow 8 AM        │
    └─────────────────────────────────────┘
    ↓
Background Processor (every minute)
    ↓
Check for due emails in database
    ↓
Send via Resend API
```

### Database Schema

**Table: `scheduled_emails`**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| session_id | TEXT | Story session ID |
| email | TEXT | Recipient email |
| chapter | INTEGER | Chapter number |
| audio_url | TEXT | MP3 file URL |
| image_url | TEXT | Chapter image URL |
| choices | TEXT | JSON array of choices |
| send_at | TEXT | ISO datetime to send |
| sent | INTEGER | 0 = pending, 1 = sent |
| created_at | TEXT | When scheduled |
| sent_at | TEXT | When sent (nullable) |
| error_message | TEXT | Error if failed |

**Table: `users`**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | TEXT | User UUID |
| email | TEXT | User email |
| session_id | TEXT | Current session |
| world_id | TEXT | Story world |
| created_at | TEXT | Account created |
| last_active | TEXT | Last activity |

## API Integration

### Start Story with Email

```python
POST /api/story/start
{
  "world_id": "west_haven",
  "email": "user@example.com"  # Optional - enables email delivery
}
```

If `email` is provided:
1. User is stored in database
2. Welcome email sent (if `SEND_WELCOME_EMAIL=true`)
3. Future chapters will be emailed

### Continue Story (Email Automatically Sent)

```python
POST /api/story/continue
{
  "session_id": "abc-123",
  "choice_id": 1
}
```

If user has email stored:
1. Story generates next chapter
2. Email scheduled (or sent immediately in dev mode)
3. API returns immediately (no waiting for email)

## Email Templates

### Welcome Email

Sent when user signs up (optional).

**Subject:** Welcome to StoryKeeper! Your story begins tomorrow.

**Content:**
- Welcome message
- Explanation of how it works
- Schedule for first chapter

### Chapter Email

Sent for each new chapter.

**Subject:** Chapter {N} is ready! 🎧

**Content:**
- Chapter number
- Audio player (inline, works in most email clients)
- Chapter image (if available)
- Choice buttons (clickable links to web app)

## Testing

### Test Immediate Email

```bash
# Set dev mode
export EMAIL_DEV_MODE=true
export RESEND_API_KEY=re_your_key_here

# Start the app
uvicorn backend.api.main:app --reload

# Make API request with your email
curl -X POST http://localhost:8000/api/story/start \
  -H "Content-Type: application/json" \
  -d '{"world_id": "west_haven", "email": "your@email.com"}'

# Make a choice - email should arrive immediately
curl -X POST http://localhost:8000/api/story/continue \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SESSION_ID", "choice_id": 1}'
```

Check your inbox!

### Test Scheduled Email

```bash
# Set production mode
export EMAIL_DEV_MODE=false

# Start the app
uvicorn backend.api.main:app --reload

# Make a choice - email will be scheduled for tomorrow 8 AM
curl -X POST http://localhost:8000/api/story/continue \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SESSION_ID", "choice_id": 1}'

# Check the database
sqlite3 email_scheduler.db "SELECT * FROM scheduled_emails;"
```

### Test Background Processor

```python
# Run manually
python -m backend.email.scheduler
```

This processes all due emails in the database.

## Production Deployment

### Railway / Heroku / Fly.io

1. **Environment Variables:**
   ```bash
   RESEND_API_KEY=re_xxxxxxxxxxxxx
   EMAIL_DEV_MODE=false
   ENABLE_EMAIL_SCHEDULER=true
   ```

2. **Background Processor:**
   The background processor starts automatically with the FastAPI app.
   It runs every minute to check for due emails.

3. **Persistent Storage:**
   Make sure `email_scheduler.db` is stored in a persistent volume:
   ```bash
   # Railway: Set storage path
   EMAIL_DB_PATH=/data/email_scheduler.db
   ```

### Email Domain Verification (Recommended)

For production, verify your domain with Resend:

1. Go to Resend Dashboard → **Domains**
2. Add your domain (e.g., `storykeeper.app`)
3. Add DNS records (SPF, DKIM, DMARC)
4. Update `from` address in `scheduler.py`:
   ```python
   "from": "StoryKeeper <story@yourdomain.com>"
   ```

Without verification, you can use `onboarding@resend.dev` (limited).

## Troubleshooting

### Emails not sending

1. **Check API key:**
   ```bash
   echo $RESEND_API_KEY
   ```

2. **Check logs:**
   ```bash
   # Should see:
   # ✓ Email system initialized successfully
   # ✓ Background email processor started
   ```

3. **Check database:**
   ```bash
   sqlite3 email_scheduler.db "SELECT * FROM scheduled_emails WHERE sent = 0;"
   ```

4. **Test Resend directly:**
   ```python
   import resend
   import os

   resend.api_key = os.getenv("RESEND_API_KEY")

   resend.Emails.send({
       "from": "StoryKeeper <story@storykeeper.app>",
       "to": ["your@email.com"],
       "subject": "Test",
       "html": "<p>Hello!</p>"
   })
   ```

### Background processor not running

Check startup logs:
```
✓ Background email processor started
```

If missing, check:
```bash
echo $ENABLE_EMAIL_SCHEDULER  # Should be "true"
```

## File Structure

```
backend/email/
├── __init__.py          # Module exports
├── database.py          # SQLite database operations
├── scheduler.py         # Email scheduling and sending
├── background.py        # APScheduler background processor
└── README.md           # This file
```

## API Reference

### `EmailScheduler`

```python
from backend.email import EmailScheduler, EmailDatabase

db = EmailDatabase("email_scheduler.db")
await db.connect()

scheduler = EmailScheduler(db)

# Schedule for later
await scheduler.schedule_chapter(
    user_email="user@example.com",
    session_id="session-123",
    chapter_number=2,
    audio_url="https://example.com/audio.mp3",
    image_url="https://example.com/image.png",
    choices=[{"id": 1, "text": "Continue"}],
    send_at=datetime(2025, 1, 15, 8, 0)
)

# Send immediately
await scheduler.send_immediate(
    user_email="user@example.com",
    session_id="session-123",
    chapter_number=2,
    audio_url="https://example.com/audio.mp3",
    image_url=None,
    choices=[{"id": 1, "text": "Continue"}]
)

# Send welcome email
await scheduler.send_welcome_email(
    user_email="user@example.com",
    first_chapter_time=datetime(2025, 1, 15, 8, 0)
)
```

## Support

- Resend Docs: https://resend.com/docs
- APScheduler Docs: https://apscheduler.readthedocs.io/

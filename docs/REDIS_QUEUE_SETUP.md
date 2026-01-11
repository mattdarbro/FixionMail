# Redis Queue Setup for FixionMail

This guide explains how to set up the Redis-based job queue for production deployments.

## Why Redis Queue?

The default single-process mode runs all workers inside the FastAPI app. This works for development but has limitations:

- **Single point of failure**: If the web server crashes, all workers stop
- **No horizontal scaling**: Can't run multiple worker instances
- **Resource contention**: Story generation blocks web requests

The Redis Queue architecture separates concerns:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Web API   │────▶│    Redis    │◀────│   Workers   │
│  (Railway)  │     │  (Upstash)  │     │  (Railway)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
              story_queue    email_queue
```

## Quick Start

### 1. Set Up Upstash Redis (Free Tier)

1. Go to [upstash.com](https://upstash.com)
2. Create a free account
3. Create a new Redis database
4. Copy the **Redis URL** (starts with `rediss://`)

### 2. Configure Environment Variables

Add these to your Railway (or .env) configuration:

```bash
# Enable Redis Queue mode
ENABLE_REDIS_QUEUE=true

# Redis connection URL from Upstash
REDIS_URL=rediss://default:xxxxx@xxxxx.upstash.io:6379
```

### 3. Deploy Process Configuration

In Railway, you'll need to create separate services:

| Service | Process | Instances |
|---------|---------|-----------|
| `web` | API Server | 1-2 |
| `worker` | Story/Email processing | 1-3 |
| `scheduler` | Daily story scheduling | 1 (only!) |
| `delivery` | Email delivery scheduling | 1 (only!) |

**Important**: Only run ONE instance of `scheduler` and `delivery` to avoid duplicate jobs.

### 4. Run Database Migration

Apply the job locking migration:

```sql
-- Run this in Supabase SQL editor
-- See: supabase/migrations/007_add_job_locking.sql
```

## Local Development

### Run Redis locally with Docker:

```bash
docker run -d --name redis -p 6379:6379 redis:alpine
```

### Set environment:

```bash
export ENABLE_REDIS_QUEUE=true
export REDIS_URL=redis://localhost:6379
```

### Start processes in separate terminals:

```bash
# Terminal 1: Web API
uvicorn backend.api.main:app --reload

# Terminal 2: Worker
python -m backend.queue.run_worker

# Terminal 3: Scheduler
python -m backend.queue.run_scheduler

# Terminal 4: Delivery
python -m backend.queue.run_delivery
```

## Architecture Details

### Queues

| Queue | Purpose | Job Timeout |
|-------|---------|-------------|
| `stories` | Story generation | 15 minutes |
| `emails` | Email delivery | 2 minutes |

### Job Flow

1. **Scheduler** checks every 60 seconds for users who need stories
2. Creates job record in Supabase `story_jobs` table
3. Enqueues job to Redis `stories` queue
4. **Worker** picks up job and generates story
5. Saves story to Supabase, schedules delivery
6. **Delivery Scheduler** checks for due deliveries every 60 seconds
7. Enqueues due deliveries to Redis `emails` queue
8. **Worker** sends email via Resend API

### Monitoring

Check queue health via API:

```bash
curl https://your-app.railway.app/api/status
```

View RQ Dashboard (if enabled):

```bash
rq-dashboard --redis-url $REDIS_URL
```

## Troubleshooting

### Jobs stuck in pending

1. Check worker is running: `rq info --url $REDIS_URL`
2. Check for errors in worker logs
3. Verify Redis connection

### Duplicate emails

1. Ensure only ONE `delivery` scheduler is running
2. Check for database constraint: `unique_story_delivery`

### Worker crashes

1. Check memory usage (story generation uses ~500MB)
2. Increase Railway service memory
3. Check for timeout issues (default: 15 min)

## Fallback Mode

If Redis is unavailable, the system falls back to single-process mode automatically. Set:

```bash
ENABLE_REDIS_QUEUE=false
```

This runs workers inside the FastAPI app using APScheduler (original behavior).

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes* | - | Redis connection URL |
| `ENABLE_REDIS_QUEUE` | No | `false` | Enable Redis queue mode |

*Required when `ENABLE_REDIS_QUEUE=true`

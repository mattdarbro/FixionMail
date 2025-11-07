# Resend Email Service Setup

## Why Resend?

✅ **3,000 emails/month free** (vs SendGrid's 100/day)
✅ **Modern, developer-friendly API**
✅ **React Email support** (easier than raw HTML)
✅ **Excellent deliverability**
✅ **5-minute setup**

## 📝 Step-by-Step Setup

### 1. Create Resend Account
1. Go to https://resend.com/signup
2. Sign up with GitHub or email
3. Verify your email

### 2. Get API Key

**For Development (No Domain Required):**
1. Go to https://resend.com/api-keys
2. Click "Create API Key"
3. Name it: `storykeeper-dev`
4. Select permissions: "Sending access"
5. Copy the key (starts with `re_`)

**Important**: Save this key! You can't see it again.

### 3. Add to Environment Variables

**Local (.env file):**
```bash
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxx
```

**Railway:**
1. Go to your Railway project
2. Click on your backend service
3. Go to "Variables" tab
4. Add new variable:
   - Key: `RESEND_API_KEY`
   - Value: `re_xxxxxxxxxxxxxxxxxxxxx`
5. Redeploy

### 4. Verify Domain (Production Only)

**For production email delivery, you need to verify your domain:**

1. Go to https://resend.com/domains
2. Click "Add Domain"
3. Enter your domain (e.g., `storykeeper.app`)
4. Add the provided DNS records to your domain:
   - SPF record
   - DKIM record
   - DMARC record (optional)
5. Wait for verification (~5-30 minutes)

**For testing**, you can skip this and use test mode (sends only to your verified email).

### 5. Test in Development

**Test Mode (No Domain Needed):**
```python
from resend import Resend

resend = Resend(api_key="re_your_key_here")

# Test email (only works with your verified email)
resend.emails.send({
    "from": "onboarding@resend.dev",  # Test sender
    "to": "your-email@example.com",   # Must be YOUR email
    "subject": "Test: StoryKeeper Chapter 1",
    "html": "<h1>This is a test</h1>"
})
```

Expected: Email arrives in ~5 seconds

## 📧 Email Template Architecture

We'll use **React Email** for clean, maintainable templates:

```
backend/email/
├── service.py              # Resend API wrapper
├── templates/
│   ├── chapter.py          # Chapter delivery email
│   └── components/
│       ├── audio_player.py # Embedded audio player
│       └── choice_button.py # Choice buttons
```

## 💰 Pricing

| Tier | Volume | Price | Cost per Email |
|------|--------|-------|----------------|
| Free | 3,000/month | $0 | $0 |
| Pro | 50,000/month | $20 | $0.0004 |
| Scale | 100,000/month | $60 | $0.0006 |

**For your use case:**
- Free tier: 100 users/month (30 chapters each = 3,000 emails)
- Pro tier: 1,666 users/month

## 🔐 Best Practices

### API Key Security
```python
# ✅ Good: Use environment variables
import os
api_key = os.getenv("RESEND_API_KEY")

# ❌ Bad: Hardcode keys
api_key = "re_123abc..."  # Never do this!
```

### Rate Limiting
Resend limits:
- **Free**: 1 email/second
- **Pro**: 10 emails/second

For batch sending, use delay:
```python
import asyncio

async def send_chapter_emails(users):
    for user in users:
        await send_chapter_email(user)
        await asyncio.sleep(1)  # 1 second delay
```

### Error Handling
```python
try:
    resend.emails.send(params)
except Exception as e:
    if "429" in str(e):
        # Rate limit - retry after delay
        await asyncio.sleep(5)
        resend.emails.send(params)
    elif "404" in str(e):
        # Invalid domain or recipient
        log_error(f"Invalid email: {recipient}")
    else:
        raise
```

## 🧪 Testing Strategy

**Phase 1: Local Testing**
- Use test mode (onboarding@resend.dev)
- Send only to your email
- Verify HTML renders correctly

**Phase 2: Staging**
- Verify your domain
- Use staging subdomain (e.g., `staging.storykeeper.app`)
- Test with team emails

**Phase 3: Production**
- Full domain verification
- Monitor deliverability dashboard
- Set up webhook for bounces

## 📊 Monitoring

**Resend Dashboard:**
- https://resend.com/emails (see all sent emails)
- https://resend.com/logs (API logs)
- https://resend.com/analytics (delivery rates)

**Key Metrics to Track:**
- ✅ Delivery rate (should be >99%)
- ⚠️ Bounce rate (should be <2%)
- 📖 Open rate (should be >40% for transactional)
- 🔗 Click rate (for choice links)

## 🆘 Troubleshooting

### "API key invalid"
- Check key starts with `re_`
- Verify no extra spaces
- Regenerate key if needed

### "Domain not verified"
- Check DNS records are added
- Wait 30 minutes for propagation
- Use `dig` to verify: `dig TXT your-domain.com`

### "Rate limit exceeded"
- Add delays between sends
- Upgrade to Pro plan ($20/month)
- Use batch API (coming soon)

### "Email not delivered"
- Check spam folder
- Verify recipient email is valid
- Check Resend logs for errors
- Ensure domain is verified (production)

## 🔄 Migration from Other Services

**From SendGrid:**
```bash
# Replace SendGrid SDK
pip uninstall sendgrid
pip install resend
```

**From AWS SES:**
```bash
# Replace boto3 email code
pip install resend
```

API is simpler - see docs: https://resend.com/docs/send-with-python

## 🎯 Next Steps

1. ✅ Create account and get API key
2. ✅ Add to `.env` and Railway
3. ⏳ Test email delivery (see `TESTING_GUIDE.md`)
4. ⏳ Create email templates (Phase 3)
5. ⏳ Set up domain verification (before production)

## 📚 Resources

- **API Docs**: https://resend.com/docs
- **React Email**: https://react.email
- **Status Page**: https://status.resend.com
- **Support**: support@resend.com

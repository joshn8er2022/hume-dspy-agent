# Security Audit Briefing for Developer Agent
**Date:** October 15, 2025
**Project:** hume-dspy-agent
**Auditor:** Claude (Security Auditor)
**Severity:** HIGH - Immediate action required

---

## Executive Summary

Your hume-dspy-agent project has been audited and **15 security vulnerabilities** were identified, including **2 CRITICAL issues** that expose production credentials in the codebase.

### Immediate Risk
- **Database credentials** (Supabase) are hardcoded and publicly accessible
- **Email service credentials** (GMass) are hardcoded and publicly accessible
- **Webhook endpoints** accept unauthenticated requests (signature verification disabled)
- **No rate limiting** allows denial-of-service attacks

---

## Critical Vulnerabilities (Fix Immediately)

### 1. Hardcoded Supabase Credentials
**Location:** `core/config.py:21-22`, `api/main.py:39-44`

```python
# CURRENT CODE (VULNERABLE):
supabase_url: Optional[str] = "https://mvjqoojihjvohstnepfm.supabase.co"
supabase_key: Optional[str] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Why this is critical:**
- Anyone with GitHub access can read/write your database
- JWT token is valid until 2075 (60-year expiration)
- All lead data, customer PII, and business data is exposed

**Fix:** Run `python3 SECURITY_FIXES.py` to automatically remove these

---

### 2. Hardcoded GMass API Key
**Location:** `api/processors.py:313`

```python
# CURRENT CODE (VULNERABLE):
GMASS_API_KEY = os.getenv("GMASS_API_KEY") or "279d97fc-9c33-49b8-b69b-94183b0305b4"
```

**Why this is critical:**
- Unauthorized email sending from your account
- Financial liability for API abuse
- Potential blacklisting of your sender domain

**Fix:** Run `python3 SECURITY_FIXES.py` to automatically remove this

---

## High Priority Issues

### 3. Webhook Signature Verification Disabled
**Location:** `utils/security.py:41-43`

**Current behavior:** Returns `True` (allows all webhooks) when no secret is configured

**Impact:**
- Anyone can send fake Typeform submissions to your endpoint
- Malicious data injection into your database
- Unauthorized email sends triggered by fake events

**Fix:** Automated script changes this to fail-closed (reject when no secret)

---

### 4. No Rate Limiting
**Location:** All webhook endpoints in `api/main.py`

**Impact:**
- Denial of service attacks
- API cost overruns (OpenAI charges per request)
- Database flooding
- Email quota exhaustion

**Fix Required:** Add rate limiting middleware (see recommendations below)

---

### 5. Debug Mode Enabled in Production
**Location:** `core/config.py:51`

```python
debug: bool = True  # DANGEROUS IN PRODUCTION
```

**Impact:**
- Stack traces expose internal architecture
- Detailed error messages help attackers
- May expose interactive debugger endpoints

**Fix:** Run `python3 SECURITY_FIXES.py` to disable by default

---

### 6. API Keys Partially Logged
**Location:** `api/processors.py:57`

```python
logger.info(f"   API key: {openai_api_key[:10]}...")  # SECURITY ISSUE
```

**Impact:**
- Reduces entropy for brute-force attacks
- Compliance violations (PCI-DSS, SOC 2)

**Fix:** Automated script removes this logging

---

## Medium Priority Issues

7. **CORS wildcard configuration** - Allows any domain to make requests
8. **No input validation** on webhook payloads - Injection attacks possible
9. **PII logged to files** - GDPR/CCPA violations (`/tmp/raw_events/`)
10. **No request size limits** - Memory exhaustion attacks
11. **Unrestricted file writes** to `/tmp` - Path traversal risks
12. **Error messages expose internals** - Information disclosure

---

## Automated Fix Script

I've created `SECURITY_FIXES.py` that automatically remediates the critical issues:

```bash
cd /Users/joshisrael/hume-dspy-agent
python3 SECURITY_FIXES.py
```

**What it fixes:**
- ✅ Removes all hardcoded credentials
- ✅ Adds environment variable validation
- ✅ Enables fail-closed webhook verification
- ✅ Disables debug mode by default
- ✅ Removes API key logging
- ✅ Creates updated `.env.example`

---

## Immediate Action Plan

### Step 1: Rotate All Exposed Credentials (NOW)
```bash
# 1. Generate new Supabase keys
#    Go to: https://app.supabase.com/project/mvjqoojihjvohstnepfm/settings/api
#    Click "Reset" on both anon and service keys

# 2. Generate new GMass API key
#    Log into GMass dashboard and regenerate API key

# 3. Check access logs for unauthorized access
#    Supabase: Settings > Database > Logs
#    GMass: Review recent email sends for suspicious activity
```

### Step 2: Apply Automated Fixes
```bash
cd /Users/joshisrael/hume-dspy-agent
python3 SECURITY_FIXES.py
```

### Step 3: Configure Environment Variables
```bash
# Copy the template
cp .env.example .env

# Edit .env and add your NEW credentials (after rotation)
nano .env

# Set these REQUIRED variables:
# - SUPABASE_URL
# - SUPABASE_KEY (use new key after rotation)
# - OPENAI_API_KEY
# - TYPEFORM_WEBHOOK_SECRET (get from Typeform dashboard)
# - GMASS_API_KEY (use new key after rotation)
```

### Step 4: Update Deployment Environment
```bash
# If deployed on Railway, update environment variables:
railway variables set SUPABASE_URL="your_url"
railway variables set SUPABASE_KEY="your_new_key"
railway variables set GMASS_API_KEY="your_new_key"
railway variables set TYPEFORM_WEBHOOK_SECRET="your_secret"
railway variables set DEBUG="false"

# Redeploy
railway up
```

### Step 5: Test Everything
```bash
# Run local tests
python3 test_agent.py

# Test webhook endpoint requires valid signature
curl -X POST http://localhost:8000/webhooks/typeform \
  -H "Content-Type: application/json" \
  -d '{"event_id": "test"}' \
  # Should return 401 Unauthorized (good!)

# Test with valid signature
# (You'll need to implement signature generation or use Typeform's test webhook)
```

---

## Additional Security Improvements Needed

After fixing the critical issues, implement these in order:

### 1. Add Rate Limiting
```bash
# Add to requirements.txt
echo "slowapi>=0.1.9" >> requirements.txt
pip install slowapi
```

Then add to `api/main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/webhooks/typeform")
@limiter.limit("10/minute")  # Max 10 webhooks per minute per IP
async def universal_webhook_receiver(...):
    # existing code
```

### 2. Add Request Size Limits
```python
# In api/main.py
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_SIZE:
        return JSONResponse(status_code=413, content={"error": "Request too large"})
    return await call_next(request)
```

### 3. Implement PII Redaction
```python
# In api/processors.py
def sanitize_for_logging(data: dict) -> dict:
    """Remove PII before logging"""
    sensitive_fields = ['email', 'phone', 'phone_number']
    sanitized = data.copy()
    for key in sensitive_fields:
        if key in sanitized:
            sanitized[key] = "***REDACTED***"
    return sanitized

# Use in logs
logger.info(f"Processing lead: {sanitize_for_logging(lead.dict())}")
```

### 4. Add Input Validation
```python
# In api/main.py
from pydantic import ValidationError

@app.post("/webhooks/typeform")
async def universal_webhook_receiver(request: Request, ...):
    try:
        payload = await request.json()
        # Validate schema
        validated = TypeformWebhookPayload(**payload)
    except ValidationError as e:
        return JSONResponse(status_code=400, content={"error": "Invalid payload"})
```

### 5. Restrict CORS
```python
# In api/main.py
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Not ["*"]
    allow_credentials=True,
    allow_methods=["POST"],  # Only needed methods
    allow_headers=["Content-Type"],
)
```

---

## Security Checklist

Track your progress:

- [ ] **CRITICAL:** Rotated Supabase keys
- [ ] **CRITICAL:** Rotated GMass API key
- [ ] **CRITICAL:** Ran `SECURITY_FIXES.py`
- [ ] **CRITICAL:** Configured all environment variables
- [ ] **CRITICAL:** Removed `.env` from git tracking
- [ ] **HIGH:** Set `TYPEFORM_WEBHOOK_SECRET` environment variable
- [ ] **HIGH:** Verified webhook signature verification works
- [ ] **HIGH:** Updated deployment environment (Railway)
- [ ] **HIGH:** Tested application with new configuration
- [ ] **MEDIUM:** Added rate limiting
- [ ] **MEDIUM:** Added request size limits
- [ ] **MEDIUM:** Implemented PII redaction in logs
- [ ] **MEDIUM:** Restricted CORS to specific origins
- [ ] **MEDIUM:** Added input validation on webhooks
- [ ] **LOW:** Set up security monitoring/alerting
- [ ] **LOW:** Documented security configurations

---

## Questions for Developer Agent

1. **Why were credentials hardcoded?**
   - Was this for quick testing/prototyping?
   - Were you aware of the security implications?

2. **Webhook signature verification:**
   - Why is it disabled by default (fail-open)?
   - Was this intentional for development ease?

3. **Production deployment:**
   - Is this currently deployed with these vulnerabilities?
   - Do you have access to check logs for unauthorized access?

4. **Environment variables:**
   - What's your deployment platform? (Railway, AWS, etc.)
   - How are secrets currently managed?

5. **Timeline:**
   - How quickly can you implement these fixes?
   - Do you need any clarification on the recommendations?

---

## Resources

- **Full Audit Report:** (See detailed 15-issue report)
- **Automated Fix Script:** `SECURITY_FIXES.py`
- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **FastAPI Security:** https://fastapi.tiangolo.com/tutorial/security/
- **Pydantic Validation:** https://docs.pydantic.dev/

---

## Contact Security Auditor

If you have questions about any of these findings or need clarification on implementation:

- Review the detailed audit report for more context
- Check `SECURITY_FIXES.py` for automated remediation
- Follow the step-by-step action plan above

**Remember:** The exposed credentials should be rotated BEFORE running the fix script, as the old credentials are already compromised.

---

**Status:** ⚠️ AWAITING RESPONSE AND ACTION FROM DEVELOPER AGENT

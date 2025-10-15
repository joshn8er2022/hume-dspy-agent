# Security Remediation Checklist
**Project:** hume-dspy-agent
**Last Updated:** October 15, 2025

Use this checklist to track your progress through the security remediation process.

---

## Phase 1: Immediate Actions (Complete within 24 hours)

### Credential Rotation (DO THIS FIRST!)

- [ ] **Rotate Supabase Keys**
  - [ ] Go to [Supabase Dashboard](https://app.supabase.com/project/mvjqoojihjvohstnepfm/settings/api)
  - [ ] Reset anon key
  - [ ] Reset service key
  - [ ] Save new keys securely (use password manager)
  - [ ] Do NOT commit new keys to git

- [ ] **Rotate GMass API Key**
  - [ ] Log into GMass dashboard
  - [ ] Navigate to API settings
  - [ ] Generate new API key
  - [ ] Revoke old key: `279d97fc-9c33-49b8-b69b-94183b0305b4`
  - [ ] Save new key securely

- [ ] **Audit Access Logs**
  - [ ] Check Supabase logs for unauthorized database access
    - Look for unusual IP addresses
    - Check for data exports or deletions
    - Review query patterns
  - [ ] Check GMass logs for unauthorized email sends
    - Review recent campaigns
    - Check for spam sends
    - Verify recipient lists

- [ ] **Get Typeform Webhook Secret**
  - [ ] Log into Typeform dashboard
  - [ ] Navigate to webhook settings for your form
  - [ ] Copy webhook secret
  - [ ] This will be needed for environment variables

---

### Apply Automated Security Fixes

- [ ] **Run the Fix Script**
  ```bash
  cd /Users/joshisrael/hume-dspy-agent
  python3 SECURITY_FIXES.py
  ```

- [ ] **Verify Changes**
  - [ ] Check `core/config.py` - no hardcoded credentials
  - [ ] Check `api/main.py` - no hardcoded credentials
  - [ ] Check `api/processors.py` - no hardcoded credentials
  - [ ] Check `utils/security.py` - fail-closed verification
  - [ ] Review `.env.example` - updated template

- [ ] **Review Git Changes**
  ```bash
  git diff
  # Make sure all hardcoded credentials are removed
  ```

---

### Configure Environment Variables

- [ ] **Create .env File**
  ```bash
  cp .env.example .env
  ```

- [ ] **Add Required Credentials** (edit `.env`)
  ```bash
  # Required
  SUPABASE_URL=https://mvjqoojihjvohstnepfm.supabase.co
  SUPABASE_KEY=<your_NEW_anon_key_here>
  SUPABASE_SERVICE_KEY=<your_NEW_service_key_here>
  OPENAI_API_KEY=<your_openai_key>
  TYPEFORM_WEBHOOK_SECRET=<your_webhook_secret>

  # Optional but recommended
  GMASS_API_KEY=<your_NEW_gmass_key_here>
  SLACK_WEBHOOK_URL=<your_slack_webhook>

  # Environment
  ENVIRONMENT=production
  DEBUG=false
  ```

- [ ] **Verify .env is Gitignored**
  ```bash
  # Check .gitignore contains:
  cat .gitignore | grep ".env"

  # If not, add it:
  echo ".env" >> .gitignore
  ```

- [ ] **Test Local Configuration**
  ```bash
  python3 test_agent.py
  # Should run without errors
  ```

---

### Update Deployment Environment

- [ ] **Update Railway Environment Variables** (if using Railway)
  ```bash
  railway variables set SUPABASE_URL="https://mvjqoojihjvohstnepfm.supabase.co"
  railway variables set SUPABASE_KEY="<new_key>"
  railway variables set SUPABASE_SERVICE_KEY="<new_service_key>"
  railway variables set OPENAI_API_KEY="<your_key>"
  railway variables set TYPEFORM_WEBHOOK_SECRET="<webhook_secret>"
  railway variables set GMASS_API_KEY="<new_gmass_key>"
  railway variables set ENVIRONMENT="production"
  railway variables set DEBUG="false"
  ```

- [ ] **Or Update Other Platform** (AWS, GCP, Heroku, etc.)
  - Document your platform's environment variable update process
  - Update all variables listed above
  - Ensure DEBUG is set to "false"

- [ ] **Redeploy Application**
  ```bash
  # Railway
  railway up

  # Or trigger redeployment via your platform's dashboard
  ```

- [ ] **Verify Deployment**
  - [ ] Application starts without errors
  - [ ] Health check endpoint responds
  - [ ] Check logs for startup errors

---

### Commit Security Fixes

- [ ] **Stage Security Fix Changes**
  ```bash
  git add core/config.py
  git add api/main.py
  git add api/processors.py
  git add utils/security.py
  git add .env.example
  git add .gitignore
  git add SECURITY_FIXES.py
  git add DEVELOPER_BRIEFING.md
  git add REMEDIATION_CHECKLIST.md
  ```

- [ ] **Verify No Credentials in Staged Files**
  ```bash
  git diff --staged | grep -i "eyJ"  # Should return nothing
  git diff --staged | grep -i "279d97fc"  # Should return nothing
  ```

- [ ] **Commit Changes**
  ```bash
  git commit -m "fix: remove hardcoded credentials and enable security features

  - Remove hardcoded Supabase credentials from config
  - Remove hardcoded GMass API key
  - Enable fail-closed webhook signature verification
  - Disable debug mode by default
  - Add environment variable validation
  - Remove API key logging

  SECURITY: All credentials have been rotated"
  ```

- [ ] **Push to Repository**
  ```bash
  git push origin main
  ```

---

## Phase 2: High Priority (Complete within 1 week)

### Implement Rate Limiting

- [ ] **Install Dependencies**
  ```bash
  pip install slowapi>=0.1.9
  echo "slowapi>=0.1.9" >> requirements.txt
  ```

- [ ] **Add Rate Limiting to api/main.py**
  - [ ] Import slowapi
  - [ ] Configure limiter
  - [ ] Add rate limits to webhook endpoints
  - [ ] Test rate limiting works

- [ ] **Test Rate Limiting**
  ```bash
  # Send 20 rapid requests, should get 429 after 10
  for i in {1..20}; do
    curl -X POST http://localhost:8000/webhooks/typeform \
      -H "Content-Type: application/json" \
      -d '{"test": true}'
    sleep 0.1
  done
  ```

---

### Add Request Size Limits

- [ ] **Implement Size Limit Middleware** in `api/main.py`
  - [ ] Add middleware function
  - [ ] Set max size to 10MB
  - [ ] Return 413 for oversized requests

- [ ] **Test Request Size Limits**
  ```bash
  # Generate 11MB payload
  dd if=/dev/zero bs=1M count=11 | curl -X POST \
    http://localhost:8000/webhooks/typeform \
    -H "Content-Type: application/json" \
    --data-binary @-
  # Should return 413 Payload Too Large
  ```

---

### Implement PII Redaction

- [ ] **Create Sanitization Function** in `utils/security.py`
  - [ ] Add `sanitize_for_logging()` function
  - [ ] Define sensitive field list
  - [ ] Redact values with "***REDACTED***"

- [ ] **Update All Logging** in `api/processors.py`
  - [ ] Replace email logging
  - [ ] Replace phone logging
  - [ ] Replace name logging
  - [ ] Use sanitize function for all PII

- [ ] **Test PII Redaction**
  - [ ] Process test webhook
  - [ ] Check logs contain no actual PII
  - [ ] Verify "***REDACTED***" appears

---

### Add Input Validation

- [ ] **Create Pydantic Models** (if not exist)
  - [ ] TypeformWebhookPayload model
  - [ ] Add field validation rules
  - [ ] Add type constraints

- [ ] **Validate Webhook Payloads** in `api/main.py`
  - [ ] Add ValidationError handling
  - [ ] Return 400 for invalid schemas
  - [ ] Log validation errors

- [ ] **Test Validation**
  ```bash
  # Send invalid payload
  curl -X POST http://localhost:8000/webhooks/typeform \
    -H "Content-Type: application/json" \
    -d '{"invalid": "schema"}'
  # Should return 400 Bad Request
  ```

---

### Restrict CORS

- [ ] **Define Allowed Origins**
  - [ ] Add `ALLOWED_ORIGINS` environment variable
  - [ ] List all legitimate domains
  - [ ] Update `.env.example`

- [ ] **Update CORS Middleware** in `api/main.py`
  - [ ] Replace `allow_origins=["*"]`
  - [ ] Use environment variable for origins
  - [ ] Restrict methods to only needed ones
  - [ ] Restrict headers to only needed ones

- [ ] **Test CORS**
  ```bash
  # Request from unauthorized origin should fail
  curl -X POST http://localhost:8000/webhooks/typeform \
    -H "Origin: http://evil.com" \
    -H "Content-Type: application/json" \
    -d '{"test": true}' \
    -v
  # Should not include CORS headers in response
  ```

---

### Verify Webhook Signature Verification

- [ ] **Test Without Signature**
  ```bash
  curl -X POST http://localhost:8000/webhooks/typeform \
    -H "Content-Type: application/json" \
    -d '{"test": true}'
  # Should return 401 Unauthorized
  ```

- [ ] **Test With Invalid Signature**
  ```bash
  curl -X POST http://localhost:8000/webhooks/typeform \
    -H "Content-Type: application/json" \
    -H "X-Typeform-Signature: invalid" \
    -d '{"test": true}'
  # Should return 401 Unauthorized
  ```

- [ ] **Test With Valid Signature**
  - [ ] Use Typeform's test webhook feature
  - [ ] Or implement signature generation for testing
  - [ ] Verify webhook processes successfully

---

## Phase 3: Medium Priority (Complete within 1 month)

### Improve File Storage Security

- [ ] **Replace /tmp with Secure Directory**
  - [ ] Create `/var/app/events` or similar
  - [ ] Set proper permissions (750)
  - [ ] Update file write code

- [ ] **Add Path Traversal Protection**
  - [ ] Validate event_id format (alphanumeric only)
  - [ ] Resolve paths and verify within allowed directory
  - [ ] Add unit tests for path validation

- [ ] **Implement File Limits**
  - [ ] Max number of files
  - [ ] Max file size
  - [ ] Automatic cleanup of old files

---

### Improve Error Handling

- [ ] **Create Generic Error Responses**
  - [ ] Remove internal details from client responses
  - [ ] Generate unique error IDs
  - [ ] Log detailed errors internally only

- [ ] **Update All Exception Handlers**
  - [ ] api/main.py
  - [ ] api/processors.py
  - [ ] agents/inbound_agent.py

- [ ] **Test Error Responses**
  - [ ] Trigger various errors
  - [ ] Verify no stack traces in responses
  - [ ] Verify error IDs are logged

---

### Add Security Headers

- [ ] **Create Security Headers Middleware**
  - [ ] X-Frame-Options: DENY
  - [ ] X-Content-Type-Options: nosniff
  - [ ] X-XSS-Protection: 1; mode=block
  - [ ] Strict-Transport-Security
  - [ ] Content-Security-Policy

- [ ] **Add Trusted Host Middleware**
  - [ ] Define allowed hosts
  - [ ] Reject requests to unknown hosts

- [ ] **Test Security Headers**
  ```bash
  curl -I http://localhost:8000/
  # Verify all security headers present
  ```

---

### Setup Security Monitoring

- [ ] **Implement Security Event Logging**
  - [ ] Log failed signature verifications
  - [ ] Log rate limit violations
  - [ ] Log authentication failures
  - [ ] Log unusual patterns

- [ ] **Setup Alerting**
  - [ ] Configure Slack/email alerts
  - [ ] Alert on repeated signature failures
  - [ ] Alert on rate limit violations
  - [ ] Alert on credential errors

- [ ] **Create Security Dashboard**
  - [ ] Track webhook verification failures
  - [ ] Monitor rate limit hits
  - [ ] Track error rates

---

## Phase 4: Low Priority (Complete within 3 months)

### HTTPS Enforcement

- [ ] **Add HTTPS Redirect Middleware** (for production)
- [ ] **Configure TLS Termination** (nginx, Caddy, or cloud provider)
- [ ] **Test HTTPS Enforcement**

---

### Secrets Management

- [ ] **Choose Secrets Manager**
  - [ ] AWS Secrets Manager
  - [ ] HashiCorp Vault
  - [ ] Google Secret Manager
  - [ ] Azure Key Vault

- [ ] **Migrate Secrets**
  - [ ] Move Supabase credentials
  - [ ] Move API keys
  - [ ] Move webhook secrets

- [ ] **Update Application** to fetch from secrets manager

- [ ] **Implement Secret Rotation**
  - [ ] Automate key rotation (30-90 days)
  - [ ] Test rotation process

---

### Security Testing

- [ ] **Run Dependency Audit**
  ```bash
  pip install pip-audit
  pip-audit
  # Fix any vulnerable dependencies
  ```

- [ ] **Run SAST (Static Analysis)**
  - [ ] Install bandit: `pip install bandit`
  - [ ] Run: `bandit -r . -ll`
  - [ ] Fix identified issues

- [ ] **Run DAST (Dynamic Analysis)**
  - [ ] Use OWASP ZAP or similar
  - [ ] Scan running application
  - [ ] Remediate findings

- [ ] **Penetration Testing**
  - [ ] Hire security professional
  - [ ] Or use automated platform (Cobalt, Synack)
  - [ ] Remediate findings

---

### Compliance & Documentation

- [ ] **GDPR Compliance**
  - [ ] Data retention policies
  - [ ] Data deletion endpoint
  - [ ] Data export endpoint
  - [ ] Consent management

- [ ] **Create Security Documentation**
  - [ ] Security architecture diagram
  - [ ] Incident response plan
  - [ ] Security runbook
  - [ ] Deployment security checklist

- [ ] **Security Training**
  - [ ] Review OWASP Top 10
  - [ ] Learn secure coding practices
  - [ ] Understand common vulnerabilities

---

## Verification & Sign-off

### Final Security Checklist

- [ ] No hardcoded credentials in codebase
- [ ] All secrets stored in environment variables or secrets manager
- [ ] Webhook signature verification enabled (fail-closed)
- [ ] Rate limiting implemented on all public endpoints
- [ ] Request size limits enforced
- [ ] PII redacted from all logs
- [ ] Input validation on all webhooks
- [ ] CORS restricted to specific origins
- [ ] Security headers configured
- [ ] Error messages don't expose internals
- [ ] Debug mode disabled in production
- [ ] HTTPS enforced in production
- [ ] Security monitoring and alerting configured
- [ ] All dependencies up to date and audited
- [ ] Deployment environment properly secured
- [ ] Incident response plan documented

---

### Testing Verification

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Security tests pass
- [ ] Manual security testing completed
- [ ] No credentials in git history
- [ ] Application functions correctly with new security measures

---

### Documentation Complete

- [ ] Security fixes documented
- [ ] Environment variables documented
- [ ] Deployment process documented
- [ ] Incident response plan documented
- [ ] Security architecture documented

---

## Notes

Use this section to track issues, questions, or additional work items:

```
[Date] [Your Name] - [Note]
Example:
2025-10-15 Josh - Started credential rotation, waiting for Supabase dashboard access
2025-10-16 Josh - Completed automated fixes, testing locally
```

---

**Progress Tracking:**
- Phase 1 (Immediate): ☐ Not Started | ☐ In Progress | ☐ Complete
- Phase 2 (High Priority): ☐ Not Started | ☐ In Progress | ☐ Complete
- Phase 3 (Medium Priority): ☐ Not Started | ☐ In Progress | ☐ Complete
- Phase 4 (Low Priority): ☐ Not Started | ☐ In Progress | ☐ Complete

**Overall Status:** ⚠️ REMEDIATION IN PROGRESS

---

*This checklist was generated as part of the security audit conducted on October 15, 2025.*

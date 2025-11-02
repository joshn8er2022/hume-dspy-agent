# Quick Typeform Testing Instructions

## Test Emails Generated

Use these emails to submit the form 3 times:

### 1. HOT Scenario
- **Email:** `test.automated.hot.{TIMESTAMP}@example.com`
- **Name:** Sarah Johnson
- **Company:** Wellness Medical Center
- **Patient Volume:** Option C (301+ patients)
- **Business Size:** Option C (Large corporation)

### 2. WARM Scenario
- **Email:** `test.automated.warm.{TIMESTAMP+1}@example.com`
- **Name:** Michael Chen
- **Company:** Family Health Clinic
- **Patient Volume:** Option B (51-300 patients)
- **Business Size:** Option B (Medium-sized business)

### 3. COLD Scenario
- **Email:** `test.automated.cold.{TIMESTAMP+2}@example.com`
- **Name:** David Williams
- **Company:** Independent Practice
- **Patient Volume:** Option A (1-50 patients)
- **Business Size:** Option A (Small business)

## Form URL
https://form.typeform.com/to/F7whHyXK#affiliate=xxxxx&wholesale_retail=xxxxx&professional=xxxxx

## After Submitting

Run validation from Railway or locally with credentials:

```bash
# If you have Supabase credentials locally
python3 validate_typeform_submissions.py --find

# Or validate specific emails
python3 validate_typeform_submissions.py \
  --hot test.automated.hot.{timestamp}@example.com \
  --warm test.automated.warm.{timestamp}@example.com \
  --cold test.automated.cold.{timestamp}@example.com
```

## Alternative: Validate via Supabase Dashboard

1. Go to Supabase dashboard
2. Query `leads` table:
   ```sql
   SELECT email, tier, qualification_score, slack_thread_ts, created_at
   FROM leads
   WHERE email LIKE 'test.automated.%'
   ORDER BY created_at DESC
   LIMIT 10;
   ```
3. Check Railway logs for processing status
4. Check Slack #inbound-leads channel for notifications


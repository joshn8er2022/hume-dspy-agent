# Typeform Automation Testing Guide

## Overview

This guide explains how to automate Typeform submissions for testing the webhook processing pipeline.

**Typeform URL:** https://form.typeform.com/to/F7whHyXK#affiliate=xxxxx&wholesale_retail=xxxxx&professional=xxxxx

## Form Structure

Based on inspection, the form contains:

### Question 1: Patient Volume (Radio Buttons)
- **Option A:** 1-50 patients
- **Option B:** 51-300 patients  
- **Option C:** 301+ patients

### Question 2: Business Size (Radio Buttons)
- **Option A:** Small business (1-5 employees)
- **Option B:** Medium-sized business (6-20 employees)
- **Option C:** Large corporation (20+ employees)

### Question 3+: Additional Fields
- First Name (text input)
- Last Name (text input)
- Email (email input)
- Company (text input)
- Phone (phone input)
- Additional fields as applicable

## Test Scenarios

### HOT Lead Scenario
- **Patient Volume:** Option C (301+ patients)
- **Business Size:** Option C (Large corporation)
- **Expected Tier:** HOT
- **Expected Score:** 70+

### WARM Lead Scenario
- **Patient Volume:** Option B (51-300 patients)
- **Business Size:** Option B (Medium-sized business)
- **Expected Tier:** WARM
- **Expected Score:** 50-69

### COLD Lead Scenario
- **Patient Volume:** Option A (1-50 patients)
- **Business Size:** Option A (Small business)
- **Expected Tier:** COLD
- **Expected Score:** 30-49

## Automation Steps

### Method 1: Using Browser Automation Tools

You can use the browser automation tools (MCP Puppeteer or browser extension) to:

1. **Navigate to form:**
   ```
   Navigate to: https://form.typeform.com/to/F7whHyXK#affiliate=xxxxx&wholesale_retail=xxxxx&professional=xxxxx
   ```

2. **Fill Question 1 (Patient Volume):**
   - Click radio button for selected option (A, B, or C)
   - Click "OK" button to proceed

3. **Fill Question 2 (Business Size):**
   - Click radio button for selected option (A, B, or C)
   - Click "OK" button to proceed

4. **Fill remaining questions:**
   - Type in First Name field
   - Type in Last Name field
   - Type in Email field (use unique timestamped email)
   - Type in Company field
   - Fill any additional fields

5. **Submit form:**
   - Click final submit button

6. **Validate webhook:**
   - Wait 30 seconds for processing
   - Check Supabase for lead record
   - Verify qualification tier and score
   - Check Slack notification

### Method 2: Using Test Script

Run the automated test script:

```bash
# Test HOT scenario
python test_typeform_puppeteer_automated.py --scenario hot

# Test WARM scenario
python test_typeform_puppeteer_automated.py --scenario warm

# Test COLD scenario
python test_typeform_puppeteer_automated.py --scenario cold

# Test all scenarios
python test_typeform_puppeteer_automated.py --all
```

The script will:
1. Generate test data for the scenario
2. Provide instructions for form filling
3. Validate webhook processing
4. Report results

## Validation Checklist

After form submission, verify:

- [ ] Lead saved to Supabase (`leads` table)
- [ ] Lead has qualification tier (HOT/WARM/COLD/UNQUALIFIED)
- [ ] Lead has qualification score (0-100)
- [ ] Slack notification created (check `#inbound-leads` channel)
- [ ] Slack thread_ts stored in lead record
- [ ] ResearchAgent state saved
- [ ] StrategyAgent state saved
- [ ] FollowUpAgent journey started (if applicable)

## Query Lead in Supabase

```sql
-- Find test lead by email
SELECT 
    id,
    email,
    first_name,
    last_name,
    company,
    tier,
    qualification_score,
    status,
    slack_thread_ts,
    slack_channel_id,
    created_at
FROM leads
WHERE email LIKE 'test.automated.%'
ORDER BY created_at DESC
LIMIT 10;

-- Check agent state
SELECT 
    lead_id,
    agent_name,
    status,
    metadata,
    created_at
FROM agent_state
WHERE lead_id = '<lead_id>'
ORDER BY created_at DESC;
```

## Phoenix Tracing

After submission, check Phoenix spans for:

- `ResearchAgent.plan_research`
- `ResearchAgent.synthesize_findings`
- `InboundAgent.analyze_business`
- `InboundAgent.analyze_engagement`
- `InboundAgent.determine_actions`
- `InboundAgent.generate_email`
- `StrategyAgent` operations

## Troubleshooting

### Lead not found in database
- Wait longer (up to 60 seconds) - webhook processing is async
- Check Railway logs for errors
- Verify webhook endpoint is correct

### Wrong tier/score
- Review test data - ensure it matches expected scenario
- Check DSPy qualification logic
- Review Phoenix spans for qualification reasoning

### No Slack notification
- Check `SLACK_BOT_TOKEN` environment variable
- Verify channel ID is correct
- Check Railway logs for Slack errors

### Form submission fails
- Verify Typeform URL is accessible
- Check for CAPTCHA or rate limiting
- Ensure all required fields are filled

## Next Steps

1. **Automate form filling** - Use Puppeteer MCP to automate browser interactions
2. **Add validation** - Enhance validation to check all system components
3. **CI/CD integration** - Add to automated test suite
4. **Performance testing** - Test with multiple concurrent submissions
5. **Edge cases** - Test with malformed data, missing fields, etc.

## Related Files

- `test_typeform_puppeteer_automated.py` - Main test script
- `scripts/automate_typeform_submission.py` - Automation helper
- `test_email_webhook.py` - Direct webhook submission (no browser)


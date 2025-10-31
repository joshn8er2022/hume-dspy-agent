# AI-Driven Tier Determination

**Status:** ✅ Implemented (Week 1 Priority)
**Expected Impact:** 15%+ conversion rate improvement
**Feature Flag:** `USE_AI_TIER_DETERMINATION`

---

## 🎯 Overview

### What Changed

**Before (Hardcoded):**
```python
if score >= 90: return SCORCHING
elif score >= 75: return HOT
elif score >= 60: return WARM
# ... rigid thresholds
```

**After (AI-Driven):**
```python
result = ai_tier_classifier.forward(
    lead=lead,
    qualification_score=score,
    engagement_data=engagement
)
# AI considers: score + engagement + context + similar leads
# Returns: tier + confidence + reasoning
```

### Why This Matters

**Problem with Hardcoded Thresholds:**
- Score 89 = HOT, Score 90 = SCORCHING (arbitrary cutoff)
- Ignores engagement signals (Calendly booking, response quality)
- Misses "hidden gems" (low score but high intent)
- Can't adapt to market changes or learn from outcomes

**AI-Driven Benefits:**
- ✅ Context-aware (considers engagement + lead profile)
- ✅ Identifies "hidden gems" (low score + Calendly = high intent)
- ✅ Transparent reasoning (explains tier assignment)
- ✅ Can be optimized with historical data (DSPy BootstrapFewShot)
- ✅ Adapts to market changes

---

## 🏗️ Architecture

### DSPy Signature: `ContextualTierDetermination`

**Input Fields:**
- `qualification_score`: Overall score (0-100)
- `engagement_signals`: Calendly booking, response quality, completion status
- `lead_context`: Company, industry, patient volume, business size, pain points
- `similar_lead_outcomes`: Historical conversion data (optional)

**Output Fields:**
- `tier`: SCORCHING, HOT, WARM, COOL, COLD, or UNQUALIFIED
- `confidence`: 0.0-1.0 (how confident is the AI?)
- `reasoning`: Why this tier? What signals matter most?

**Instructions to AI:**
```
Determine lead tier based on holistic context, not just score.

Consider:
- Qualification score (baseline)
- Engagement signals (Calendly booking = strong intent)
- Lead context (large practice + healthcare = better fit)
- Industry norms (telehealth boom = higher priority)

Don't rely solely on score thresholds. A score of 89 with Calendly 
booking might be SCORCHING, while a score of 91 with no engagement 
might be just HOT.

Identify "hidden gems" - leads with lower scores but high intent signals.
```

### Module: `AITierClassifier`

**Location:** `dspy_modules/tier_determination.py`

**Key Methods:**
- `forward(lead, qualification_score, engagement_data)` - Main classification
- `_build_engagement_signals(lead, engagement_data)` - Format engagement context
- `_build_lead_context(lead)` - Format lead profile
- `_get_similar_lead_outcomes(lead)` - Historical data lookup (TODO)

---

## 🚀 How to Use

### Enable AI Tier Determination

**In Railway (Production):**
```bash
# Set environment variable
USE_AI_TIER_DETERMINATION=true
```

**In Local Development:**
```bash
# Add to .env
USE_AI_TIER_DETERMINATION=true

# Or export for current session
export USE_AI_TIER_DETERMINATION=true
```

### Disable (Fallback to Hardcoded)

```bash
USE_AI_TIER_DETERMINATION=false
# Or remove the environment variable
```

---

## 🧪 Testing

### Run Test Script

```bash
# Test with hardcoded thresholds (baseline)
USE_AI_TIER_DETERMINATION=false python test_ai_tier_determination.py

# Test with AI-driven classification
USE_AI_TIER_DETERMINATION=true python test_ai_tier_determination.py
```

### Test Scenarios

**Scenario 1: Hidden Gem**
- Score: 65 (WARM by hardcoded)
- Engagement: Calendly booking + complete submission
- Expected AI: HOT or SCORCHING (high intent despite lower score)

**Scenario 2: High Score, Low Engagement**
- Score: 92 (SCORCHING by hardcoded)
- Engagement: Partial submission, no Calendly
- Expected AI: HOT (lower intent despite high score)

**Scenario 3: Medium Score, Good Engagement**
- Score: 70 (WARM by hardcoded)
- Engagement: Complete submission, detailed use case
- Expected AI: WARM or HOT (engaged lead)

---

## 📊 A/B Testing Plan

### Phase 1: Validation (Week 1, Days 1-2)

**Goal:** Verify AI tier determination works correctly

**Steps:**
1. Deploy with `USE_AI_TIER_DETERMINATION=false` (safe)
2. Run test script with sample leads
3. Verify AI reasoning makes sense
4. Check for errors in logs

**Success Criteria:**
- ✅ No errors in AI classification
- ✅ AI reasoning is logical and specific
- ✅ Confidence scores are reasonable (>0.7)

### Phase 2: A/B Test (Week 1, Days 3-5)

**Goal:** Measure conversion improvement

**Implementation:**
```python
# In InboundAgent._determine_tier
import random
use_ai_tier = (
    os.getenv("USE_AI_TIER_DETERMINATION", "false").lower() == "true" and
    random.random() < 0.5  # 50% of leads use AI
)
```

**Metrics to Track:**
- Conversion rate (AI vs hardcoded)
- Tier distribution (are tiers changing?)
- Sales team feedback (qualitative)
- "Hidden gems" identified (low score + high conversion)

**Success Criteria:**
- ✅ 10%+ conversion improvement for AI group
- ✅ No increase in false positives (SCORCHING leads that don't convert)
- ✅ Sales team approves AI tier assignments

### Phase 3: Full Rollout (Week 1, Days 6-7)

**If Phase 2 succeeds:**
1. Set `USE_AI_TIER_DETERMINATION=true` for 100% of leads
2. Monitor for 48 hours
3. Measure conversion improvement
4. Celebrate 15%+ conversion increase! 🎉

---

## 🔧 Optimization (Week 2+)

### Collect Training Data

**Goal:** Optimize AI classifier with historical conversion data

**Data Needed:**
- 100+ labeled leads with:
  - Lead profile (company, industry, volume)
  - Qualification score
  - Engagement signals
  - Assigned tier
  - **Conversion outcome** (did they buy?)

**Query:**
```sql
SELECT 
    id, email, company, industry,
    qualification_score, tier,
    calendly_url, response_type,
    converted, conversion_date
FROM leads
WHERE created_at >= NOW() - INTERVAL '90 days'
    AND qualification_score IS NOT NULL
    AND tier IS NOT NULL
ORDER BY created_at DESC
LIMIT 100;
```

### DSPy Optimization

**Use BootstrapFewShot:**
```python
from dspy.teleprompt import BootstrapFewShot

# Define metric
def tier_accuracy_metric(example, prediction, trace=None):
    # Did the AI tier match the actual conversion outcome?
    # SCORCHING/HOT leads should convert at >50%
    # WARM leads should convert at >30%
    # etc.
    return prediction.tier == example.optimal_tier

# Optimize
optimizer = BootstrapFewShot(
    metric=tier_accuracy_metric,
    max_bootstrapped_demos=8,
    max_labeled_demos=4
)

optimized_classifier = optimizer.compile(
    AITierClassifier(),
    trainset=labeled_leads
)

# Save optimized version
optimized_classifier.save('optimized_tier_classifier.json')
```

**Expected Improvement:**
- 20%+ accuracy improvement over baseline
- Better "hidden gem" detection
- Industry-specific tier calibration

---

## 📈 Success Metrics

### Quantitative

**Conversion Rate:**
- Baseline (Hardcoded): X%
- Target (AI): X% + 15%
- Measurement: Track conversion by tier over 30 days

**"Hidden Gems" Identified:**
- Leads with score <75 but converted
- Baseline: Y leads/month
- Target: Y + 50% (AI identifies more)

**Tier Distribution:**
- Track if AI assigns different tiers than hardcoded
- Expect: More nuanced tier assignments

### Qualitative

**Sales Team Feedback:**
- Do AI tier assignments make sense?
- Are "hidden gems" actually high-intent?
- Is AI reasoning helpful for prioritization?

**AI Confidence:**
- Average confidence score >0.75
- Low confidence (<0.6) triggers manual review

---

## 🐛 Troubleshooting

### AI Tier Determination Not Working

**Check:**
1. Environment variable set: `echo $USE_AI_TIER_DETERMINATION`
2. DSPy configured: Check logs for "DSPy configured with..."
3. API key available: `echo $OPENROUTER_API_KEY`

**Logs to Look For:**
```
🤖 AI Tier Classification:
   Score: 65
   AI Tier: HOT
   Confidence: 0.85
   Reasoning: Despite moderate score, Calendly booking indicates...
```

### AI Errors

**If AI fails:**
- System automatically falls back to hardcoded thresholds
- Error logged: "❌ AI tier determination failed: {error}"
- Lead still gets processed (no data loss)

---

## 🔮 Future Enhancements

### Week 2+

1. **Historical Data Integration**
   - Implement `_get_similar_lead_outcomes()`
   - Query Supabase for similar lead conversions
   - Use outcomes to inform tier decisions

2. **DSPy Optimization**
   - Collect 100+ labeled leads
   - Run BootstrapFewShot optimization
   - Deploy optimized classifier

3. **Multi-Model Ensemble**
   - Use multiple LLMs (Sonnet, GPT-4, Gemini)
   - Aggregate predictions for higher confidence
   - Fallback chain for reliability

4. **Real-Time Learning**
   - Update classifier as new conversions happen
   - Continuous improvement loop
   - A/B test new optimizations automatically

---

## 📋 Implementation Checklist

- ✅ Created `dspy_modules/tier_determination.py`
- ✅ Updated `agents/inbound_agent.py`
- ✅ Created `test_ai_tier_determination.py`
- ✅ Created this documentation
- ⏳ Test with sample leads
- ⏳ Deploy to production (feature flag OFF)
- ⏳ Enable A/B testing (50% AI, 50% hardcoded)
- ⏳ Measure conversion improvement
- ⏳ Full rollout if >10% improvement

---

**Next Steps:** Run tests, deploy, and measure results!

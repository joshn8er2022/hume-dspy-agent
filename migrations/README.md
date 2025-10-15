# Database Migrations

## Required Tables

### 1. `raw_events` Table
Event sourcing table for all incoming webhooks.

**Run Migration:**
```sql
-- Go to Supabase Dashboard → SQL Editor
-- Copy and paste: migrations/001_create_raw_events_table.sql
-- Click "Run"
```

### 2. `leads` Table
Qualified leads with AI scoring and follow-up tracking.

**Run Migration:**
```sql
-- Go to Supabase Dashboard → SQL Editor
-- Copy and paste: migrations/002_create_leads_table.sql
-- Click "Run"
```

---

## Quick Setup (Supabase Dashboard)

1. Go to: https://supabase.com/dashboard/project/umawnwaoahhuttbeyuxs/sql
2. Click "New Query"
3. Copy contents of `001_create_raw_events_table.sql`
4. Paste and click "Run"
5. Repeat for `002_create_leads_table.sql`

---

## Verify Tables Created

```sql
-- Check tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('raw_events', 'leads');

-- Should return:
-- raw_events
-- leads
```

---

## Table Schemas

### `raw_events`
```
id                UUID PRIMARY KEY
event_type        TEXT NOT NULL
source            TEXT NOT NULL (e.g., 'typeform', 'slack')
raw_payload       JSONB NOT NULL
headers           JSONB
received_at       TIMESTAMPTZ NOT NULL
processed_at      TIMESTAMPTZ
status            TEXT (pending, processing, success, failed)
error             TEXT
created_at        TIMESTAMPTZ
updated_at        TIMESTAMPTZ
```

### `leads`
```
id                      UUID PRIMARY KEY
typeform_id             TEXT UNIQUE
form_id                 TEXT
first_name              TEXT
last_name               TEXT
email                   TEXT
phone                   TEXT
company                 TEXT
qualification_score     INTEGER (0-100)
qualification_tier      TEXT (HOT, WARM, COLD, UNQUALIFIED)
qualification_reasoning TEXT
recommended_actions     JSONB
status                  TEXT (new, contacted, following_up, responded, cold)
follow_up_count         INTEGER
last_follow_up_at       TIMESTAMPTZ
response_received       BOOLEAN
escalated               BOOLEAN
slack_thread_ts         TEXT
slack_channel           TEXT
raw_answers             JSONB
raw_metadata            JSONB
created_at              TIMESTAMPTZ
updated_at              TIMESTAMPTZ
```

---

## Notes

- Both tables have Row Level Security (RLS) enabled
- Service role has full access
- Anonymous role can insert (for webhooks)
- Indexes created for common queries
- Auto-updating `updated_at` timestamp triggers

"""Fix Supabase schema - add missing tier column and verify structure.

Run this to fix the database schema error: column leads.tier does not exist
"""

import os
import sys
from supabase import create_client

def fix_schema():
    """Add missing tier column and verify schema matches lead model."""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)
    
    supabase = create_client(supabase_url, supabase_key)
    
    print("🔍 Checking leads table schema...")
    
    # Check if tier column exists
    try:
        result = supabase.table('leads').select('tier').limit(1).execute()
        print("✅ tier column exists!")
    except Exception as e:
        error_msg = str(e)
        if 'column leads.tier does not exist' in error_msg:
            print("❌ tier column missing - attempting to add it...")
            
            # This won't work via Supabase client - need SQL
            print("\n⚠️  Cannot add column via Supabase client.")
            print("   You need to run this SQL in Supabase dashboard:")
            print("\n   SQL Editor → New Query → Run this:")
            print("""
   -- Add tier column
   ALTER TABLE leads ADD COLUMN IF NOT EXISTS tier TEXT;
   
   -- Add index for performance
   CREATE INDEX IF NOT EXISTS idx_leads_tier ON leads(tier);
   
   -- Optionally set default
   UPDATE leads SET tier = 'UNQUALIFIED' WHERE tier IS NULL;
""")
            print("\n   After running, test again with: python scripts/fix_supabase_schema.py")
            sys.exit(1)
        else:
            print(f"❌ Unexpected error: {error_msg}")
            sys.exit(1)
    
    # Verify all expected columns exist
    print("\n✅ Verifying all columns...")
    
    expected_columns = [
        'id', 'typeform_id', 'form_id', 'email', 'first_name', 'last_name',
        'company', 'tier', 'qualification_score', 'status', 'created_at'
    ]
    
    try:
        # Try to select all expected columns
        query = supabase.table('leads').select(','.join(expected_columns)).limit(1)
        result = query.execute()
        print(f"✅ All {len(expected_columns)} columns verified!")
        
        # Show sample data
        if result.data:
            print("\n📊 Sample lead data:")
            lead = result.data[0]
            print(f"   Name: {lead.get('first_name')} {lead.get('last_name')}")
            print(f"   Email: {lead.get('email')}")
            print(f"   Tier: {lead.get('tier', 'NULL')}")
            print(f"   Score: {lead.get('qualification_score', 'NULL')}")
        else:
            print("⚠️  No leads in database yet")
        
    except Exception as e:
        print(f"❌ Column verification failed: {e}")
        print("\nMissing columns need to be added. See SQL above.")
        sys.exit(1)
    
    print("\n✅ Schema is correct!")
    print("   Agent should now be able to query lead data.")


if __name__ == "__main__":
    fix_schema()

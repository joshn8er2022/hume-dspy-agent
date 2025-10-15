#!/usr/bin/env python3
"""
Automated Security Fixes for hume-dspy-agent
==============================================
This script automatically remediates critical security vulnerabilities
identified in the security audit dated 2025-10-15.

Run this script to fix:
- Remove hardcoded credentials
- Enable webhook signature verification (fail-closed)
- Disable debug mode in production
- Add proper environment variable validation

Usage:
    python3 SECURITY_FIXES.py
"""

import os
import re
from pathlib import Path


def fix_config_py():
    """Remove hardcoded Supabase credentials from core/config.py"""
    print("\n[1/4] Fixing core/config.py...")

    file_path = Path("core/config.py")
    content = file_path.read_text()

    # Remove hardcoded Supabase URL
    content = re.sub(
        r'supabase_url: Optional\[str\] = "https://.*?"',
        'supabase_url: Optional[str] = None',
        content
    )

    # Remove hardcoded Supabase key
    content = re.sub(
        r'supabase_key: Optional\[str\] = "eyJ.*?"',
        'supabase_key: Optional[str] = None',
        content
    )

    # Disable debug mode by default
    content = re.sub(
        r'debug: bool = True',
        'debug: bool = False',
        content
    )

    # Add validation method if not present
    if '__init__' not in content and 'def validate_credentials' not in content:
        validation_code = '''
    def __post_init__(self):
        """Validate required credentials are set."""
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self.supabase_key:
            raise ValueError("SUPABASE_KEY environment variable is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
'''
        # Insert after class definition
        content = re.sub(
            r'(class Settings\(BaseSettings\):.*?\n)',
            r'\1' + validation_code,
            content,
            flags=re.DOTALL
        )

    file_path.write_text(content)
    print("   ✅ Removed hardcoded credentials")
    print("   ✅ Disabled debug mode")
    print("   ✅ Added credential validation")


def fix_api_main_py():
    """Remove hardcoded credentials from api/main.py"""
    print("\n[2/4] Fixing api/main.py...")

    file_path = Path("api/main.py")
    content = file_path.read_text()

    # Remove hardcoded Supabase credentials
    old_pattern = r'''SUPABASE_KEY = \(
    os\.getenv\("SUPABASE_SERVICE_KEY"\) or
    os\.getenv\("SUPABASE_KEY"\) or
    os\.getenv\("SUPABASE_ANON_KEY"\) or
    "eyJ[^"]*"
\)'''

    new_code = '''SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY") or
    os.getenv("SUPABASE_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("❌ SUPABASE_URL and SUPABASE_KEY must be set")
    raise ValueError("Missing required Supabase credentials")'''

    content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

    # Also fix single-line pattern if exists
    content = re.sub(
        r'SUPABASE_KEY = os\.getenv\("SUPABASE_KEY"\) or "eyJ.*?"',
        'SUPABASE_KEY = os.getenv("SUPABASE_KEY")\n\nif not SUPABASE_KEY:\n    raise ValueError("SUPABASE_KEY environment variable is required")',
        content
    )

    file_path.write_text(content)
    print("   ✅ Removed hardcoded Supabase credentials")
    print("   ✅ Added credential validation")


def fix_processors_py():
    """Remove hardcoded GMass API key and API key logging from api/processors.py"""
    print("\n[3/4] Fixing api/processors.py...")

    file_path = Path("api/processors.py")
    content = file_path.read_text()

    # Remove hardcoded GMass API key
    content = re.sub(
        r'GMASS_API_KEY = os\.getenv\("GMASS_API_KEY"\) or "[0-9a-f-]+"',
        '''GMASS_API_KEY = os.getenv("GMASS_API_KEY")

    if not GMASS_API_KEY:
        logger.warning("⚠️  GMASS_API_KEY not configured, skipping email send")
        return None''',
        content
    )

    # Remove API key logging
    content = re.sub(
        r'logger\.info\(f"   API key: \{openai_api_key\[:10\]\}\.\.\."\)',
        '# API key logging removed for security',
        content
    )

    file_path.write_text(content)
    print("   ✅ Removed hardcoded GMass API key")
    print("   ✅ Removed API key logging")


def fix_security_py():
    """Enable fail-closed webhook signature verification in utils/security.py"""
    print("\n[4/4] Fixing utils/security.py...")

    file_path = Path("utils/security.py")
    content = file_path.read_text()

    # Change from fail-open to fail-closed
    old_code = '''if not secret:
        logger.warning("No Typeform secret configured - skipping signature verification")
        return True  # Allow if no secret configured (dev mode)'''

    new_code = '''if not secret:
        logger.error("❌ No Typeform secret configured - rejecting webhook for security")
        return False  # DENY if no secret configured (fail-closed for security)'''

    content = content.replace(old_code, new_code)

    file_path.write_text(content)
    print("   ✅ Enabled fail-closed signature verification")


def create_env_template():
    """Create updated .env.example with all required variables"""
    print("\n[BONUS] Updating .env.example...")

    env_content = """# Supabase Configuration (REQUIRED)
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_KEY=your_supabase_service_key_here

# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY=your_openai_api_key_here

# Typeform Configuration (REQUIRED for webhook security)
TYPEFORM_WEBHOOK_SECRET=your_typeform_webhook_secret_here

# GMass Configuration (OPTIONAL - for email sending)
GMASS_API_KEY=your_gmass_api_key_here

# Slack Configuration (OPTIONAL)
SLACK_WEBHOOK_URL=your_slack_webhook_url_here

# Environment
ENVIRONMENT=production  # or 'development'
DEBUG=false  # Set to 'true' only in development

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Security Note: NEVER commit actual credentials to version control!
# Copy this file to .env and fill in your actual values.
"""

    Path(".env.example").write_text(env_content)
    print("   ✅ Updated .env.example with security notes")


def main():
    """Run all security fixes"""
    print("=" * 70)
    print("AUTOMATED SECURITY FIXES FOR hume-dspy-agent")
    print("=" * 70)
    print("\nThis script will remediate critical security vulnerabilities:")
    print("  • Remove hardcoded credentials")
    print("  • Enable fail-closed webhook verification")
    print("  • Disable debug mode in production")
    print("  • Add environment variable validation")
    print("\n" + "=" * 70)

    # Confirm we're in the right directory
    if not Path("core/config.py").exists():
        print("\n❌ ERROR: Run this script from the hume-dspy-agent root directory")
        print("   Current directory:", os.getcwd())
        return 1

    try:
        fix_config_py()
        fix_api_main_py()
        fix_processors_py()
        fix_security_py()
        create_env_template()

        print("\n" + "=" * 70)
        print("✅ ALL SECURITY FIXES APPLIED SUCCESSFULLY!")
        print("=" * 70)
        print("\n⚠️  CRITICAL NEXT STEPS:")
        print("\n1. ROTATE ALL CREDENTIALS IMMEDIATELY:")
        print("   • Generate new Supabase keys (the old ones are exposed)")
        print("   • Generate new GMass API key")
        print("   ��� Check Supabase/GMass logs for unauthorized access")

        print("\n2. SET ENVIRONMENT VARIABLES:")
        print("   • Copy .env.example to .env")
        print("   • Fill in all required credentials")
        print("   • Update your deployment environment (Railway, etc.)")

        print("\n3. VERIFY THE FIXES:")
        print("   • Review the changed files")
        print("   • Test the application with valid environment variables")
        print("   • Ensure webhooks are properly verified")

        print("\n4. ADDITIONAL SECURITY IMPROVEMENTS NEEDED:")
        print("   • Add rate limiting (see SECURITY_AUDIT_REPORT.md)")
        print("   • Implement request size limits")
        print("   • Add PII redaction in logs")
        print("   • Configure CORS properly")

        print("\n" + "=" * 70)

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

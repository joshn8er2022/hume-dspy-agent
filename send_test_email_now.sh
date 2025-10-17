#!/bin/bash
# Auto-approve test email send to buildoutinc@gmail.com

cd /Users/joshisrael/hume-dspy-agent

echo "🚀 Sending test email to buildoutinc@gmail.com (auto-approved)..."
echo ""

# Auto-approve by piping 'yes' to the script
echo "yes" | python3 test_email_webhook.py

echo ""
echo "✅ Test complete!"
echo ""
echo "Check results:"
echo "  📧 Email: buildoutinc@gmail.com inbox (30-60 seconds)"
echo "  💬 Slack: #inbound-leads channel"
echo "  📊 GMass: https://www.gmass.co/app/campaigns"
echo "  🗄️ Supabase: leads table"

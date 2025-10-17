#!/bin/bash
# Setup Slack environment variables for Railway

echo "🔧 Slack Agent Caller - Railway Configuration"
echo "=============================================="
echo ""

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found"
    echo "Install with: npm i -g @railway/cli"
    exit 1
fi

echo "Please provide your Slack credentials:"
echo ""

# Get Bot Token
read -p "📝 Enter SLACK_BOT_TOKEN (starts with xoxb-): " slack_bot_token
if [[ ! $slack_bot_token =~ ^xoxb- ]]; then
    echo "❌ Invalid token format. Should start with 'xoxb-'"
    exit 1
fi

echo "✅ Bot token looks valid"
echo ""

# Get User ID
read -p "📝 Enter JOSH_SLACK_DM_CHANNEL (your user ID, starts with U): " user_id
if [[ ! $user_id =~ ^U ]]; then
    echo "❌ Invalid user ID format. Should start with 'U'"
    exit 1
fi

echo "✅ User ID looks valid"
echo ""

# Confirm
echo "Ready to set Railway variables:"
echo "  SLACK_BOT_TOKEN: ${slack_bot_token:0:20}..."
echo "  JOSH_SLACK_DM_CHANNEL: $user_id"
echo ""
read -p "Continue? (yes/no): " confirm

if [[ $confirm != "yes" ]]; then
    echo "❌ Cancelled by user"
    exit 1
fi

echo ""
echo "🚀 Setting Railway environment variables..."

# Set variables
railway variables set SLACK_BOT_TOKEN="$slack_bot_token"
railway variables set JOSH_SLACK_DM_CHANNEL="$user_id"

echo ""
echo "✅ Environment variables set!"
echo ""
echo "Railway will automatically redeploy with new variables."
echo "Wait 2-3 minutes for deployment to complete."
echo ""
echo "Then test by sending a DM to your bot: 'help'"
echo ""

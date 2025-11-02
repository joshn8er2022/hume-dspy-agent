#!/bin/bash
# Railway CLI Variables Checker
# This script helps check which environment variables are configured in Railway

echo "==================================================================="
echo "RAILWAY ENVIRONMENT VARIABLES CHECK"
echo "==================================================================="
echo ""
echo "Make sure Railway CLI is installed and you're logged in:"
echo "  railway login"
echo ""
echo "Set your project (if needed):"
echo "  railway link"
echo ""
echo "==================================================================="
echo "Checking variables..."
echo "==================================================================="
echo ""

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found!"
    echo ""
    echo "Install it with:"
    echo "  npm i -g @railway/cli"
    echo "  OR"
    echo "  brew install railway"
    exit 1
fi

echo "✅ Railway CLI found"
echo ""

# List all variables
echo "📋 ALL ENVIRONMENT VARIABLES:"
echo "----------------------------"
railway variables

echo ""
echo "==================================================================="
echo "CATEGORIZED VARIABLES CHECK"
echo "==================================================================="
echo ""

# Define all variables we care about
declare -a critical_vars=(
    "SUPABASE_URL"
    "SUPABASE_SERVICE_KEY"
    "OPENROUTER_API_KEY"
    "OPENAI_API_KEY"
    "SLACK_BOT_TOKEN"
    "GMASS_API_KEY"
    "FROM_EMAIL"
)

declare -a high_value_vars=(
    "MCP_SERVER_URL"
    "CLEARBIT_API_KEY"
    "WOLFRAM_APP_ID"
)

declare -a optional_vars=(
    "SENDGRID_API_KEY"
    "CLOSE_API_KEY"
    "APOLLO_API_KEY"
    "PERPLEXITY_API_KEY"
    "ANTHROPIC_API_KEY"
    "PHOENIX_API_KEY"
    "PHOENIX_ENDPOINT"
    "PHOENIX_PROJECT_NAME"
)

# Function to check if variable exists
check_var() {
    local var_name=$1
    # Railway CLI doesn't have a direct way to check single var, so we list all and grep
    if railway variables 2>/dev/null | grep -q "^${var_name}="; then
        echo "  ✅ ${var_name}"
        return 0
    else
        echo "  ❌ ${var_name} - NOT SET"
        return 1
    fi
}

echo "🔴 CRITICAL (Required for core functionality):"
echo "----------------------------------------------"
critical_count=0
for var in "${critical_vars[@]}"; do
    if check_var "$var"; then
        ((critical_count++))
    fi
done
echo "   Status: ${critical_count}/${#critical_vars[@]} configured"
echo ""

echo "🟡 HIGH VALUE (Unlocks major features):"
echo "----------------------------------------"
high_value_count=0
for var in "${high_value_vars[@]}"; do
    if check_var "$var"; then
        ((high_value_count++))
    fi
done
echo "   Status: ${high_value_count}/${#high_value_vars[@]} configured"
echo ""

echo "🟢 OPTIONAL (Nice to have):"
echo "---------------------------"
optional_count=0
for var in "${optional_vars[@]}"; do
    if check_var "$var"; then
        ((optional_count++))
    fi
done
echo "   Status: ${optional_count}/${#optional_vars[@]} configured"
echo ""

echo "==================================================================="
echo "SUMMARY"
echo "==================================================================="
total_vars=$((${#critical_vars[@]} + ${#high_value_vars[@]} + ${#optional_vars[@]}))
total_configured=$((critical_count + high_value_count + optional_count))
echo "Total Variables Checked: ${total_vars}"
echo "Configured: ${total_configured}/${total_vars} ($((total_configured * 100 / total_vars))%)"
echo ""
echo "📖 See docs/COMPLETE_TOOL_INVENTORY.md for details on each variable"
echo ""


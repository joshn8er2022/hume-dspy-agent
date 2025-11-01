#!/bin/bash
# Get all Railway deployment information
# Run this after logging in with: railway login --browserless

echo "=========================================="
echo "🚂 RAILWAY DEPLOYMENT INFORMATION"
echo "=========================================="
echo ""

# Link to project (if not already linked)
echo "🔗 Linking to project..."
railway link 2>&1 || echo "Already linked or failed to link"
echo ""

# Get environment variables
echo "=========================================="
echo "📋 ENVIRONMENT VARIABLES"
echo "=========================================="
railway variables 2>&1
echo ""

# Check deployment status
echo "=========================================="
echo "📊 DEPLOYMENT STATUS"
echo "=========================================="
railway status 2>&1
echo ""

# Get recent deployment logs
echo "=========================================="
echo "📝 RECENT LOGS (last 50 lines)"
echo "=========================================="
railway logs --lines 50 2>&1
echo ""

# List all services
echo "=========================================="
echo "🔧 SERVICES"
echo "=========================================="
railway service list 2>&1 || railway list 2>&1
echo ""

# Get project info
echo "=========================================="
echo "ℹ️  PROJECT INFO"
echo "=========================================="
railway whoami 2>&1
echo ""

echo "=========================================="
echo "✅ Information gathering complete!"
echo "=========================================="
echo ""
echo "📤 Saving output to railway_info.txt..."

#!/bin/bash
# Railway CLI Setup Script
# This script will help you install and configure Railway CLI

set -e

echo "🚂 Railway CLI Setup"
echo "===================="
echo ""

# Check if Railway is already installed
if command -v railway &> /dev/null; then
    echo "✅ Railway CLI is already installed"
    railway --version
    echo ""
else
    echo "📦 Installing Railway CLI..."
    echo ""
    
    # Try to install Railway CLI
    bash -c "$(curl -fsSL https://railway.app/install.sh)" || {
        echo ""
        echo "⚠️  Automated installation failed. Please install manually:"
        echo ""
        echo "Option 1 - Using Homebrew:"
        echo "  brew install railway"
        echo ""
        echo "Option 2 - Using npm:"
        echo "  npm install -g @railway/cli"
        echo ""
        echo "Option 3 - Manual download:"
        echo "  Visit: https://docs.railway.app/develop/cli#install"
        echo ""
        exit 1
    }
fi

echo ""
echo "🔐 Logging into Railway..."
echo "   (This will open a browser window)"
echo ""
railway login

echo ""
echo "🔗 Linking to hume-dspy-agent project..."
echo ""
railway link

echo ""
echo "✅ Setup complete!"
echo ""
echo "📊 Available commands:"
echo "  railway variables          - List all environment variables"
echo "  railway logs               - View deployment logs"
echo "  railway status             - Check deployment status"
echo "  railway up                 - Deploy current directory"
echo "  railway open               - Open project in browser"
echo ""
echo "🔍 Checking your environment variables..."
echo ""
railway variables

echo ""
echo "🚀 Ready to deploy!"
echo ""
echo "To deploy your current changes, run:"
echo "  ./DEPLOY_NOW.sh"
echo ""

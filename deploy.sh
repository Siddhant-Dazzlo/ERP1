#!/bin/bash

# Railway Deployment Script
# This script helps prepare your application for Railway deployment

echo "🚀 Preparing SaaS ERP for Railway deployment..."

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Please run this script from the project root."
    exit 1
fi

# Check if required files exist
echo "📋 Checking required files..."

required_files=("railway.json" "Procfile" "nixpacks.toml" "requirements.txt")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file is missing"
        exit 1
    fi
done

# Check if environment variables template exists
if [ -f "railway.env.example" ]; then
    echo "✅ railway.env.example exists"
else
    echo "❌ railway.env.example is missing"
    exit 1
fi

# Check if database initialization script exists
if [ -f "init_db.py" ]; then
    echo "✅ init_db.py exists"
else
    echo "❌ init_db.py is missing"
    exit 1
fi

echo ""
echo "🎉 All required files are present!"
echo ""
echo "📝 Next steps:"
echo "1. Push your code to a Git repository (GitHub, GitLab, or Bitbucket)"
echo "2. Go to https://railway.app and create a new project"
echo "3. Connect your Git repository"
echo "4. Add PostgreSQL and Redis services"
echo "5. Set up environment variables using railway.env.example as reference"
echo "6. Deploy!"
echo ""
echo "📖 For detailed instructions, see RAILWAY_DEPLOYMENT.md"
echo ""
echo "🔗 Useful links:"
echo "- Railway Dashboard: https://railway.app"
echo "- Railway Docs: https://docs.railway.app"
echo "- Railway Discord: https://discord.gg/railway"
#!/bin/bash

echo "=========================================="
echo "AI Dropshipping ERP - Deployment Script"
echo "=========================================="
echo ""

# Check Python version
echo "🔍 Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if not exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys!"
fi

# Initialize database
echo "🗄️  Initializing database..."
python3 init_db.py

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p static/processed_images
mkdir -p static/exports
mkdir -p static/css
mkdir -p static/js

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "=========================================="
echo "🚀 To start the server, run:"
echo "   source venv/bin/activate"
echo "   python3 app.py"
echo ""
echo "📡 Server will be available at:"
echo "   http://localhost:5000"
echo ""
echo "👤 Default login credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "⚠️  IMPORTANT:"
echo "   1. Edit .env file with your API keys"
echo "   2. Change default password after first login"
echo "   3. Configure Coupang static IP for API access"
echo "=========================================="

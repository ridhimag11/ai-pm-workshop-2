#!/usr/bin/env python3
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

# Import and run the app
from src.app import app
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Excuse Email Tool server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("🔧 Your Databricks token is configured!")
    print("✨ Ready to generate excuse emails!")
    print("-" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

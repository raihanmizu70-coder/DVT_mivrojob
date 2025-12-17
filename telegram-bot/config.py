import os

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8506336833:AAHqTala7chpEiJJ2W1s6lSN5qgwdJpC5b8")
TELEGRAM_ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "6561117046"))

# Backend API
BACKEND_URL = os.getenv("BACKEND_URL", "https://dvt-backend.onrender.com")

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "dvt-cloud")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "764846719658924")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "OmdiuCF8")

# Admin
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Mizu123@@")

# Web App URL
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-frontend.vercel.app")

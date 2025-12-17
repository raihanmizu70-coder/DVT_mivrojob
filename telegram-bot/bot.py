import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests
import os
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8506336833:AAHqTala7chpEiJJ2W1s6lSN5qgwdJpC5b8")
ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "6561117046"))
BACKEND_URL = os.getenv("BACKEND_URL", "https://dvt-backend.onrender.com")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    
    # Check if user is admin
    if user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📊 Admin Dashboard", web_app={"url": f"{BACKEND_URL}/admin"})],
            [InlineKeyboardButton("🧩 Manage Tasks", callback_data='manage_tasks')],
            [InlineKeyboardButton("📋 Review Submissions", callback_data='review_submissions')],
            [InlineKeyboardButton("💸 Process Withdrawals", callback_data='process_withdrawals')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👑 Welcome back, Admin {first_name}!\n\n"
            "Use the buttons below to manage the system:",
            reply_markup=reply_markup
        )
        return
    
    # Regular user
    refer_code = None
    if context.args:
        refer_code = context.args[0]
    
    # Register user in backend
    try:
        response = requests.post(f"{BACKEND_URL}/api/user", json={
            "telegram_id": user_id,
            "username": username,
            "first_name": first_name,
            "refer_code": refer_code
        })
        
        if response.status_code == 200:
            user_data = response.json()
            # Welcome message with Mini App button
            keyboard = [
                [InlineKeyboardButton("🎯 Open Mini App", web_app={"url": "https://your-frontend.vercel.app"})],
                [InlineKeyboardButton("👥 Refer & Earn", callback_data='refer')],
                [InlineKeyboardButton("📊 My Earnings", callback_data='earnings')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"👋 Welcome {first_name} to DVT Mini App!\n\n"
                "💸 Earn money by completing simple tasks\n"
                "🧩 Complete micro jobs and get paid\n"
                "👥 Refer friends for extra bonus\n\n"
                "Click the button below to start earning:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("Welcome! Use /start to begin.")
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        await update.message.reply_text("Welcome! Use /start to begin.")

# Admin commands
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use admin commands.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Admin Dashboard", web_app={"url": f"{BACKEND_URL}/admin"})],
        [InlineKeyboardButton("🧩 Add New Task", callback_data='add_task')],
        [InlineKeyboardButton("📋 Review Pending", callback_data='review_pending')],
        [InlineKeyboardButton("💰 Process Withdrawals", callback_data='process_withdraw')],
        [InlineKeyboardButton("👥 User Management", callback_data='manage_users')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👑 Admin Panel\n\n"
        "Select an option:",
        reply_markup=reply_markup
    )

# Withdrawal notification
async def notify_withdrawal_request(user_id: int, amount: float, method: str, account: str):
    """Send notification to admin about new withdrawal request"""
    try:
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        message = (
            "💰 New Withdrawal Request\n\n"
            f"👤 User ID: {user_id}\n"
            f"💸 Amount: ৳{amount}\n"
            f"🏦 Method: {method}\n"
            f"📱 Account: {account}\n\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await app.bot.send_message(
            chat_id=ADMIN_ID,
            text=message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f'approve_wd_{user_id}'),
                 InlineKeyboardButton("❌ Reject", callback_data=f'reject_wd_{user_id}')]
            ])
        )
    except Exception as e:
        logger.error(f"Error sending withdrawal notification: {e}")

# Callback query handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'refer':
        # Get user's referral code
        user_id = query.from_user.id
        try:
            response = requests.get(f"{BACKEND_URL}/api/user/{user_id}")
            if response.status_code == 200:
                user_data = response.json()
                refer_code = user_data.get('refer_code', f'DVT-{user_id}')
                refer_link = f"https://t.me/digitalvishon_1235bot?start={refer_code}"
                
                await query.edit_message_text(
                    f"👥 Refer & Earn\n\n"
                    f"🎯 Your Referral Code: `{refer_code}`\n\n"
                    f"🔗 Your Referral Link:\n{refer_link}\n\n"
                    "💰 You earn ৳5 for every friend who makes their first withdrawal!\n\n"
                    "Share your code with friends and start earning!",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error getting referral info: {e}")
            await query.edit_message_text("Error loading referral information.")
    
    elif data == 'earnings':
        user_id = query.from_user.id
        try:
            response = requests.get(f"{BACKEND_URL}/api/user/{user_id}")
            if response.status_code == 200:
                user_data = response.json()
                balance = user_data.get('balance', 0)
                cash_wallet = user_data.get('cash_wallet', 0)
                
                await query.edit_message_text(
                    f"💰 Your Earnings\n\n"
                    f"💼 Main Wallet: ৳{balance:.2f}\n"
                    f"💳 Cash Wallet: ৳{cash_wallet:.2f}\n\n"
                    "💸 Withdraw from Cash Wallet\n"
                    "🧩 Complete more tasks to earn more!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💸 Withdraw", callback_data='withdraw')],
                        [InlineKeyboardButton("🧩 Find Tasks", web_app={"url": "https://your-frontend.vercel.app"})]
                    ])
                )
        except Exception as e:
            logger.error(f"Error getting earnings: {e}")
    
    elif data.startswith('approve_wd_') or data.startswith('reject_wd_'):
        # Admin approving/rejecting withdrawals
        user_id = int(data.split('_')[2])
        action = 'approve' if data.startswith('approve') else 'reject'
        
        if query.from_user.id != ADMIN_ID:
            await query.answer("❌ You are not authorized!", show_alert=True)
            return
        
        # TODO: Implement withdrawal approval/rejection logic
        if action == 'approve':
            await query.edit_message_text(f"✅ Withdrawal approved for user {user_id}")
        else:
            await query.edit_message_text(f"❌ Withdrawal rejected for user {user_id}")

# Main function
def main():
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

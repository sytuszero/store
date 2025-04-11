import os
import logging
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("No BOT_TOKEN found in .env file")
    exit(1)

# GitHub Pages URL for your Mini App
MINI_APP_URL = "https://sytuszero.github.io/telegram-store/"
logger.info(f"Using Mini App URL: {MINI_APP_URL}")

# Orders storage (in memory for demo)
orders = {}

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message and display Mini App button."""
    keyboard = [
        [InlineKeyboardButton("📱 Open Store", web_app=WebAppInfo(url=MINI_APP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Welcome to our Fashion Store, {update.effective_user.first_name}!\n\n"
        "Click the button below to browse our products:",
        reply_markup=reply_markup
    )

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle data received from the Web App."""
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        user_id = update.effective_user.id
        
        # Store the order
        if user_id not in orders:
            orders[user_id] = []
        
        orders[user_id].append(data)
        
        # Format order message
        order_text = "🛍️ *Your Order*\n\n"
        
        total = 0
        for item in data.get('items', []):
            item_price = item.get('price', 0) * item.get('quantity', 1)
            total += item_price
            order_text += f"• {item.get('name')} x{item.get('quantity')} - ${item_price:.2f}\n"
        
        order_text += f"\n💰 *Total: ${total:.2f}*\n\n"
        order_text += "Thank you for your order! Our team will contact you shortly to arrange payment and delivery."
        
        # Send confirmation to user
        await update.effective_message.reply_text(
            order_text,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error processing web app data: {e}")
        await update.effective_message.reply_text(
            "Sorry, there was an error processing your order. Please try again."
        )

def main():
    """Start the bot."""
    # Create the Telegram application
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    # Start the bot
    logger.info("Starting Telegram bot...")
    logger.info(f"Mini App URL: {MINI_APP_URL}")
    logger.info("Send /start to your bot in Telegram to access the store")
    application.run_polling()

if __name__ == '__main__':
    # Start the bot
    main() 
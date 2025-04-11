import os
import json
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from dotenv import load_dotenv
from functools import wraps

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['DATABASE'] = 'store.db'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Telegram bot token
TOKEN = os.getenv("BOT_TOKEN")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Database Setup
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Create users table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0
    )
    ''')
    
    # Create categories table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    ''')
    
    # Create products table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT,
        image_url TEXT,
        category_id INTEGER,
        sizes TEXT,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    ''')
    
    # Insert default admin user if not exists
    admin = conn.execute('SELECT * FROM users WHERE username = ?', 
                        (os.getenv("ADMIN_USERNAME", "admin"),)).fetchone()
    
    if not admin:
        default_password = os.getenv("ADMIN_PASSWORD", "admin")
        hashed_password = generate_password_hash(default_password)
        conn.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)',
                    (os.getenv("ADMIN_USERNAME", "admin"), hashed_password))
    
    # Insert default categories if not exist
    default_categories = ['tshirts', 'jeans', 'shoes', 'dresses']
    for category in default_categories:
        conn.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category,))
    
    conn.commit()
    conn.close()

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        
        conn = get_db_connection()
        user = conn.execute('SELECT is_admin FROM users WHERE id = ?', 
                          (session['user_id'],)).fetchone()
        conn.close()
        
        if not user or user['is_admin'] != 1:
            flash('Admin privileges required')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('admin_dashboard')
                
            return redirect(next_page)
        
        flash('Invalid username or password')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/products')
@admin_required
def admin_products():
    conn = get_db_connection()
    products = conn.execute('''
        SELECT p.*, c.name as category_name 
        FROM products p 
        LEFT JOIN categories c ON p.category_id = c.id
    ''').fetchall()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    
    return render_template('admin_products.html', products=products, categories=categories)

@app.route('/admin/products/add', methods=['POST'])
@admin_required
def add_product():
    name = request.form['name']
    price = float(request.form['price'])
    description = request.form['description']
    category_id = int(request.form['category_id'])
    sizes = request.form['sizes']  # Comma-separated sizes
    
    image_url = ''
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO products (name, price, description, image_url, category_id, sizes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, price, description, image_url, category_id, sizes))
    conn.commit()
    conn.close()
    
    flash('Product added successfully')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_product(id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        category_id = int(request.form['category_id'])
        sizes = request.form['sizes']
        
        image_url = request.form['current_image']
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = url_for('static', filename=f'uploads/{filename}')
        
        conn.execute('''
            UPDATE products
            SET name = ?, price = ?, description = ?, image_url = ?, category_id = ?, sizes = ?
            WHERE id = ?
        ''', (name, price, description, image_url, category_id, sizes, id))
        conn.commit()
        
        flash('Product updated successfully')
        return redirect(url_for('admin_products'))
    
    product = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    
    return render_template('edit_product.html', product=product, categories=categories)

@app.route('/admin/products/<int:id>/delete', methods=['POST'])
@admin_required
def delete_product(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Product deleted successfully')
    return redirect(url_for('admin_products'))

@app.route('/admin/categories')
@admin_required
def admin_categories():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    
    return render_template('admin_categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['POST'])
@admin_required
def add_category():
    name = request.form['name'].lower()
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO categories (name) VALUES (?)', (name,))
        conn.commit()
        flash('Category added successfully')
    except sqlite3.IntegrityError:
        flash('Category already exists')
    
    conn.close()
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/<int:id>/delete', methods=['POST'])
@admin_required
def delete_category(id):
    conn = get_db_connection()
    
    # Check if category is in use
    products = conn.execute('SELECT COUNT(*) as count FROM products WHERE category_id = ?', 
                           (id,)).fetchone()
    
    if products['count'] > 0:
        flash('Cannot delete category that has products')
    else:
        conn.execute('DELETE FROM categories WHERE id = ?', (id,))
        conn.commit()
        flash('Category deleted successfully')
    
    conn.close()
    return redirect(url_for('admin_categories'))

# API Endpoints
@app.route('/api/products')
def get_products():
    category = request.args.get('category', 'all')
    
    conn = get_db_connection()
    
    if category == 'all':
        products = conn.execute('''
            SELECT p.*, c.name as category
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
        ''').fetchall()
    else:
        products = conn.execute('''
            SELECT p.*, c.name as category
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE c.name = ?
        ''', (category,)).fetchall()
    
    conn.close()
    
    # Convert to JSON serializable format
    result = []
    for product in products:
        sizes = product['sizes'].split(',') if product['sizes'] else []
        result.append({
            'id': product['id'],
            'name': product['name'],
            'price': product['price'],
            'category': product['category'],
            'image': product['image_url'],
            'description': product['description'],
            'sizes': sizes
        })
    
    return jsonify(result)

@app.route('/api/categories')
def get_categories():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    
    return jsonify([{'id': c['id'], 'name': c['name']} for c in categories])

# Mini App route
@app.route('/')
def index():
    return render_template('index.html')

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message and display Mini App button."""
    mini_app_url = f"{WEBHOOK_URL}" if WEBHOOK_URL else f"https://{HOST}/static/index.html"
    
    keyboard = [
        [InlineKeyboardButton("📱 Open Store", web_app=WebAppInfo(url=mini_app_url))]
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

@app.route('/api/webhook', methods=['POST'])
async def telegram_webhook():
    """Handle Telegram webhook."""
    update = Update.de_json(request.get_json(force=True), application.bot)
    
    # Process incoming updates
    await application.process_update(update)
    
    return 'ok'

# Initialize the application
def initialize():
    # Initialize database
    init_db()
    
    # Setup Telegram bot
    global application
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    # Setup webhook if URL is provided
    if WEBHOOK_URL:
        application.bot.set_webhook(f"{WEBHOOK_URL}/api/webhook")
        logger.info(f"Webhook set to {WEBHOOK_URL}/api/webhook")
    else:
        # Start polling if no webhook
        logger.info("Starting bot with polling")
        import asyncio
        from threading import Thread

        def run_bot():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(application.run_polling())

        Thread(target=run_bot).start()

# Initialize on startup
if __name__ == '__main__':
    initialize()
    app.run(host=HOST, port=PORT)
else:
    initialize() 

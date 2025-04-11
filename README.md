# Telegram Store Admin

A full-featured Telegram Mini App store with admin panel for managing products and categories.

## Features

### Store Features
- Product catalog with categories
- Product details with size selection
- Shopping cart functionality
- Checkout process with order confirmation
- Integration with Telegram's Mini App platform
- Responsive design that adapts to Telegram's theme

### Admin Features
- Secure admin login
- Product management (add, edit, delete)
- Category management (add, delete)
- Image upload for products
- User-friendly interface

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-folder>
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Edit the `.env` file and update the following:

```
BOT_TOKEN=your_telegram_bot_token
ADMIN_USERNAME=your_preferred_username
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=your_random_secret_key
```

### 4. Run Locally

```bash
python app.py
```

The app will start on http://localhost:5000

### 5. Deploy to Railway

1. Create a Railway account at https://railway.app/
2. Install Railway CLI (optional)
3. Create a new project in Railway
4. Connect your GitHub repository or deploy directly
5. Set environment variables in Railway dashboard
6. Add the `WEBHOOK_URL` environment variable with your Railway app URL
7. Deploy your application

```bash
# Using Railway CLI
railway login
railway link
railway up
```

### 6. Configure Telegram Bot

1. Talk to BotFather on Telegram
2. Use the `/newbot` command to create a new bot
3. Set up your bot's name and username
4. Save the bot token and add it to your `.env` file
5. Use the `/setdomain` command to set your Mini App domain
   - Format: `/setdomain @YourBot your-railway-app.up.railway.app`

## Accessing the Admin Panel

1. Go to `/admin/login` on your deployed application
2. Log in with the credentials set in the `.env` file
3. Manage products and categories through the admin interface

## API Endpoints

- `GET /api/products` - Get all products or filter by category
- `GET /api/categories` - Get all categories

## License

This project is available under the MIT license. 
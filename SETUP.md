# FinTrack - Setup Instructions

## Quick Setup Guide for Running on Any PC

### Prerequisites
- Python 3.12+ installed
- Git installed
- Terminal/Command Prompt access

### Step 1: Clone the Repository
```bash
git clone https://github.com/aryangorde8/Fintrack.git
cd Fintrack/backend
```

### Step 2: Create Virtual Environment
```bash
# On Linux/Mac
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run Database Migrations
```bash
python manage.py migrate
```

### Step 5: Create Admin User (Optional)
```bash
python manage.py createsuperuser
```

### Step 6: Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### Step 7: Run the Server
```bash
python manage.py runserver
```

### Step 8: Access the Application
Open your browser and go to:
- **Main App**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/

## Default Login
The app uses automatic registration - just enter any username and password on the login page, and it will create an account for you!

## Troubleshooting

### Error: "No module named 'django'"
```bash
pip install -r requirements.txt
```

### Error: "Database is locked"
```bash
rm db.sqlite3
python manage.py migrate
```

### Static files not loading
```bash
python manage.py collectstatic --noinput
```

### Port already in use
```bash
# Use a different port
python manage.py runserver 8080
```

## Features to Test
1. **Login/Register** - Create an account
2. **Dashboard** - View financial overview with charts
3. **Budgets** - Create budget limits for categories
4. **Transactions** - Add income/expense transactions
5. **Reports** - Generate CSV/PDF reports
6. **Budget Alerts** - Get popup notifications when exceeding budget limits

## Environment Variables (Optional)
Create a `.env` file for optional features:
```
SECRET_KEY=your-secret-key
DEBUG=True
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_FROM_NUMBER=your-phone-number
```

## Tech Stack
- Django 5.2.7
- Django REST Framework
- SQLite (default, PostgreSQL for production)
- Chart.js for visualizations
- WhiteNoise for static files

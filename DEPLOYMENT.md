# FinTrack - Deployment Guide

## GitHub Deployment

### 1. Initial Setup
```bash
# Add all changes
git add .

# Commit changes
git commit -m "Complete FinTrack project with black & neon theme"

# Push to GitHub
git push origin main
```

### 2. Environment Variables
Create a `.env` file (not tracked by git) with:
```
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DATABASE_URL=your-database-url  # For production (PostgreSQL)

# Optional: Twilio for SMS alerts
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_FROM_NUMBER=your-twilio-number
```

## Render.com Deployment

The project is already configured for Render with `render.yaml`, `Procfile`, and `runtime.txt`.

### Steps:
1. Push code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Render will auto-detect settings from `render.yaml`
6. Add environment variables in Render dashboard
7. Deploy!

### Important Settings:
- **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- **Start Command**: `gunicorn core.wsgi:application`
- **Python Version**: 3.12.3 (from runtime.txt)

## Heroku Deployment

```bash
# Install Heroku CLI
heroku login

# Create new app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Set environment variables
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DEBUG=False
heroku config:set DISABLE_COLLECTSTATIC=1

# Deploy
git push heroku main

# Run migrations
heroku run python manage.py migrate

# Collect static files
heroku run python manage.py collectstatic --noinput

# Create superuser
heroku run python manage.py createsuperuser
```

## Railway Deployment

1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Initialize: `railway init`
4. Deploy: `railway up`
5. Add PostgreSQL: `railway add postgresql`
6. Set environment variables in Railway dashboard

## Manual Server Deployment (VPS)

### Prerequisites:
- Ubuntu 20.04+ server
- Python 3.12.3
- PostgreSQL
- Nginx
- Supervisor

### Steps:

1. **Clone repository**
```bash
git clone https://github.com/yourusername/fintrack.git
cd fintrack/backend
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with production settings
```

4. **Setup database**
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

5. **Configure Gunicorn**
```bash
gunicorn --bind 0.0.0.0:8000 core.wsgi:application
```

6. **Setup Nginx**
Create `/etc/nginx/sites-available/fintrack`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        alias /path/to/fintrack/backend/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

7. **Setup Supervisor** (for process management)
Create `/etc/supervisor/conf.d/fintrack.conf`:
```ini
[program:fintrack]
command=/path/to/fintrack/backend/venv/bin/gunicorn core.wsgi:application --bind 0.0.0.0:8000
directory=/path/to/fintrack/backend
user=youruser
autostart=true
autorestart=true
```

## Post-Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Static files collected
- [ ] Admin user created
- [ ] ALLOWED_HOSTS updated
- [ ] DEBUG=False in production
- [ ] SSL certificate installed (Let's Encrypt)
- [ ] Database backups configured
- [ ] Monitoring setup (optional)

## Security Notes

1. Never commit `.env` file
2. Use strong SECRET_KEY (generate with: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`)
3. Always set DEBUG=False in production
4. Use HTTPS in production
5. Regular security updates

## Troubleshooting

### Static files not loading
```bash
python manage.py collectstatic --noinput
```

### Database errors
```bash
python manage.py migrate
```

### Permission errors
```bash
chmod +x manage.py
chown -R www-data:www-data /path/to/fintrack
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/aryangorde8/fintrack/issues
- Email: aryangorde8@gmail.com

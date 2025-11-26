# FinTrack

Personal finance and budget monitoring app built with Django and Django REST Framework. It offers a responsive web dashboard, JWT-secured APIs, and optional SMS/email notifications when budgets exceed their thresholds.

## Highlights

- Modern dashboard with 30-day spend trends, top categories, and recent activity snapshots.
- REST API for budgets, transactions, and reports backed by JWT authentication.
- CSV and PDF export endpoints for quick reporting.
- Optional alerts via Twilio SMS and SMTP email integrations.
- Interactive CLI (`interactive_fintrack.py`) for terminal-driven budgeting.

## Requirements

- Python 3.10+
- SQLite (bundled) or a PostgreSQL database via `DATABASE_URL`
- pip packages listed in `requirements.txt`

## Quick Start

1. **Install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configure environment (optional)**
   - Copy `.env.example` (if you create one) or set environment variables such as `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, and Twilio credentials.
   - For email alerts, set `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`.
3. **Apply migrations and create a superuser (optional)**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. **Run the server**
   ```bash
   python manage.py runserver
   ```
5. Visit `http://localhost:8000/api/web/login/` to explore the UI.

## Running Tests

Automated tests focus on the budgeting APIs and the enriched dashboard context.

```bash
python manage.py test api
```

## API Overview

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/budgets/` | GET/POST | List budgets or create/update a budget for the authenticated user |
| `/api/transactions/` | GET/POST | List or create transactions with automatic budget roll-ups |
| `/api/reports/summary/` | GET | Aggregated totals and budget utilization |
| `/api/reports/export/csv/` | GET | Download transactions as CSV |
| `/api/reports/export/pdf/` | GET | Download transactions as PDF |

JWT authentication endpoints live under `/api/auth/`.

## Deployment Notes

- Static assets are served via WhiteNoise. Run `python manage.py collectstatic` before deploying.
- Set `DEBUG=false` and provide a strong `SECRET_KEY` in production.
- `render.yaml` and `Procfile` are configured for deployment to Render. Update environment variables there as needed.

## Interview-Worthy Extras

- The dashboard now visualizes spending trends and risk budgets for rapid storytelling.
- SMS and email hooks demonstrate extensibility into real-world alerting.
- Tests cover critical budgeting logic and ensure analytics stay accurate as the project evolves.

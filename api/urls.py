from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, LoginView, health,
    BudgetListCreateView, TransactionListCreateView,
    ReportSummaryView, ExportCSVView, ExportPDFView
)
from .web_views import login_view, dashboard, budgets_view, transactions_view, report_view, download_csv, download_pdf

app_name = 'api'

urlpatterns = [
    # API endpoints
    path('health/', health, name='health'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('budgets/', BudgetListCreateView.as_view(), name='budgets'),
    path('transactions/', TransactionListCreateView.as_view(), name='transactions'),
    path('reports/summary/', ReportSummaryView.as_view(), name='report-summary'),
    path('reports/export/csv/', ExportCSVView.as_view(), name='report-export-csv'),
    path('reports/export/pdf/', ExportPDFView.as_view(), name='report-export-pdf'),

    # Web interface
    path('web/login/', login_view, name='web-login'),
    path('web/dashboard/', dashboard, name='web-dashboard'),
    path('web/budgets/', budgets_view, name='web-budgets'),
    path('web/transactions/', transactions_view, name='web-transactions'),
    path('web/report/', report_view, name='web-report'),
    path('web/download/csv/', download_csv, name='web-download-csv'),
    path('web/download/pdf/', download_pdf, name='web-download-pdf'),
]

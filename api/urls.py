from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, LoginView, health,
    BudgetListCreateView, TransactionListCreateView,
    ReportSummaryView, ExportCSVView, ExportPDFView
)
from .web_views import login_view, dashboard, budgets_view, transactions_view, report_view, download_csv, download_pdf

urlpatterns = [
    # API endpoints
    path('health/', health),
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('auth/token/refresh/', TokenRefreshView.as_view()),
    path('budgets/', BudgetListCreateView.as_view()),
    path('transactions/', TransactionListCreateView.as_view()),
    path('reports/summary/', ReportSummaryView.as_view()),
    path('reports/export/csv/', ExportCSVView.as_view()),
    path('reports/export/pdf/', ExportPDFView.as_view()),
    
    # Web interface
    path('web/login/', login_view),
    path('web/dashboard/', dashboard),
    path('web/budgets/', budgets_view),
    path('web/transactions/', transactions_view),
    path('web/report/', report_view),
    path('web/download/csv/', download_csv),
    path('web/download/pdf/', download_pdf),
]

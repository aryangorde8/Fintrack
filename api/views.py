import csv
from decimal import Decimal
from django.db.models import Sum, Count
from django.contrib.auth.models import User
from django.http import HttpResponse
from rest_framework import permissions, generics, views
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from .models import Budget, Transaction, Notification
from .serializers import RegisterSerializer, BudgetSerializer, TransactionSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health(request):
    return Response({'status': 'OK'})

class BudgetListCreateView(generics.ListCreateAPIView):
    serializer_class = BudgetSerializer
    
    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        category = self.request.data.get('category')
        limit_amount = Decimal(str(self.request.data.get('limit_amount', 0)))
        alert_threshold = int(self.request.data.get('alert_threshold', 80))
        
        budget, created = Budget.objects.get_or_create(
            user=self.request.user,
            category=category,
            defaults={'limit_amount': limit_amount, 'alert_threshold': alert_threshold}
        )
        
        if not created:
            budget.limit_amount = limit_amount
            budget.alert_threshold = alert_threshold
            budget.save()
        
        serializer.instance = budget

class TransactionListCreateView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by('-date')
    
    def perform_create(self, serializer):
        transaction = serializer.save(user=self.request.user)
        
        if transaction.type == 'expense':
            budget, created = Budget.objects.get_or_create(
                user=self.request.user,
                category=transaction.category,
                defaults={'limit_amount': 0, 'spent_amount': 0, 'alert_threshold': 80}
            )
            
            budget.spent_amount += transaction.amount
            budget.save()
            
            if budget.limit_amount > 0:
                percentage = (budget.spent_amount / budget.limit_amount) * 100
                if percentage >= budget.alert_threshold:
                    Notification.objects.create(
                        user=self.request.user,
                        type='budget_alert',
                        message=f'Budget alert: {int(percentage)}% of {transaction.category} budget used'
                    )

class ReportSummaryView(views.APIView):
    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user)
        budgets = Budget.objects.filter(user=request.user)
        
        income_total = transactions.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        expense_total = transactions.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
        
        budget_data = []
        for budget in budgets:
            budget_data.append({
                'category': budget.category,
                'limit_amount': budget.limit_amount,
                'spent_amount': budget.spent_amount,
                'remaining': budget.limit_amount - budget.spent_amount,
                'utilization_pct': int((budget.spent_amount / budget.limit_amount) * 100) if budget.limit_amount > 0 else 0
            })
        
        return Response({
            'summary': {
                'totalIncome': income_total,
                'totalExpenses': expense_total,
                'netAmount': income_total - expense_total
            },
            'budgetAnalysis': budget_data
        })

class ExportCSVView(views.APIView):
    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user).order_by('date')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="fintrack-report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Description'])
        
        for t in transactions:
            writer.writerow([
                t.date.strftime('%Y-%m-%d'),
                t.type,
                t.category,
                str(t.amount),
                t.description
            ])
        
        return response

class ExportPDFView(views.APIView):
    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user).order_by('date')
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="fintrack-report.pdf"'
        
        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        y = height - 50
        
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, y, "FinTrack Transaction Report")
        y -= 40
        
        p.setFont("Helvetica", 10)
        for t in transactions[:30]:
            text = f"{t.date.strftime('%Y-%m-%d')} | {t.type} | {t.category} | {t.amount}"
            p.drawString(50, y, text)
            y -= 15
            if y < 50:
                p.showPage()
                y = height - 50
        
        p.showPage()
        p.save()
        return response

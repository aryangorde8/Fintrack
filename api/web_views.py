from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from decimal import Decimal
from .models import Budget, Transaction, Notification
from .sms_utils import send_sms_alert

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect('/api/web/dashboard/')
        else:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(username=username, password=password)
                user = authenticate(username=username, password=password)
                login(request, user)
                return redirect('/api/web/dashboard/')
    return render(request, 'login.html')

@login_required(login_url='/api/web/login/')
def dashboard(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user)
    income_total = sum(t.amount for t in transactions.filter(type='income'))
    expense_total = sum(t.amount for t in transactions.filter(type='expense'))
    net_amount = income_total - expense_total
    
    budgets = Budget.objects.filter(user=user)
    budget_warnings = []
    for budget in budgets:
        if budget.limit_amount > 0:
            percentage = int((budget.spent_amount / budget.limit_amount) * 100)
            if percentage >= budget.alert_threshold:
                budget_warnings.append(f"⚠️ Budget alert: {percentage}% of {budget.category} budget used (₹{budget.spent_amount}/₹{budget.limit_amount})")
    
    return render(request, 'dashboard.html', {
        'income_total': income_total,
        'expense_total': expense_total,
        'net_amount': net_amount,
        'budget_warnings': budget_warnings
    })

@login_required(login_url='/api/web/login/')
def budgets_view(request):
    user = request.user
    
    if request.method == 'POST':
        category = request.POST.get('category')
        limit_amount = Decimal(request.POST.get('limit_amount'))
        alert_threshold = int(request.POST.get('alert_threshold'))
        
        budget, created = Budget.objects.get_or_create(
            user=user, category=category,
            defaults={'limit_amount': limit_amount, 'alert_threshold': alert_threshold}
        )
        if not created:
            budget.limit_amount = limit_amount
            budget.alert_threshold = alert_threshold
            budget.save()
        
        messages.success(request, f"Budget '{category}' saved successfully!")
        return redirect('/api/web/budgets/')
    
    budgets = Budget.objects.filter(user=user)
    budget_list = []
    for b in budgets:
        percentage = int((b.spent_amount / b.limit_amount * 100)) if b.limit_amount > 0 else 0
        budget_list.append({
            'category': b.category,
            'limit_amount': b.limit_amount,
            'spent_amount': b.spent_amount,
            'remaining': b.limit_amount - b.spent_amount,
            'percentage': percentage,
            'alert_threshold': b.alert_threshold
        })
    
    return render(request, 'budgets.html', {'budgets': budget_list})

@login_required(login_url='/api/web/login/')
def transactions_view(request):
    user = request.user
    
    if request.method == 'POST':
        tx_type = request.POST.get('type')
        amount = Decimal(request.POST.get('amount'))
        category = request.POST.get('category')
        description = request.POST.get('description', '')
        phone_number = request.POST.get('phone_number', '')
        
        transaction = Transaction.objects.create(
            user=user, amount=amount, type=tx_type,
            category=category, description=description
        )
        
        if tx_type == 'expense':
            budget, _ = Budget.objects.get_or_create(
                user=user, category=category,
                defaults={'limit_amount': 0, 'spent_amount': 0, 'alert_threshold': 80}
            )
            budget.spent_amount += amount
            budget.save()
            
            if budget.limit_amount > 0:
                percentage = (budget.spent_amount / budget.limit_amount) * 100
                if percentage >= budget.alert_threshold:
                    alert_msg = f'FinTrack Alert: {int(percentage)}% of {category} budget used (₹{budget.spent_amount}/₹{budget.limit_amount})'
                    
                    # Save notification
                    Notification.objects.create(
                        user=user, type='budget_alert',
                        message=alert_msg
                    )
                    
                    # Send SMS if phone number provided
                    if phone_number:
                        success, result = send_sms_alert(phone_number, alert_msg)
                        if success:
                            messages.success(request, f'📱 SMS alert sent to {phone_number}!')
                        else:
                            messages.warning(request, f'⚠️ SMS failed: {result}')
                    
                    messages.warning(request, alert_msg)
        
        messages.success(request, 'Transaction added successfully!')
        return redirect('/api/web/transactions/')
    
    transactions = Transaction.objects.filter(user=user).order_by('-date')[:20]
    return render(request, 'transactions.html', {'transactions': transactions})

@login_required(login_url='/api/web/login/')
def report_view(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user)
    budgets = Budget.objects.filter(user=user)
    
    income_total = sum(t.amount for t in transactions.filter(type='income'))
    expense_total = sum(t.amount for t in transactions.filter(type='expense'))
    
    budget_analysis = []
    for b in budgets:
        budget_analysis.append({
            'category': b.category,
            'limit_amount': b.limit_amount,
            'spent_amount': b.spent_amount,
            'remaining': b.limit_amount - b.spent_amount,
            'utilization_pct': int((b.spent_amount / b.limit_amount) * 100) if b.limit_amount > 0 else 0
        })
    
    return render(request, 'report.html', {
        'summary': {
            'totalIncome': income_total,
            'totalExpenses': expense_total,
            'netAmount': income_total - expense_total
        },
        'budget_analysis': budget_analysis
    })

@login_required(login_url='/api/web/login/')
def download_csv(request):
    import csv
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by('date')
    
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

@login_required(login_url='/api/web/login/')
def download_pdf(request):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by('date')
    
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

import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Sum, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import Budget, Transaction, Notification

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect('api:web-dashboard')
        else:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(username=username, password=password)
                user = authenticate(username=username, password=password)
                login(request, user)
                return redirect('api:web-dashboard')
    return render(request, 'login.html')

@login_required(login_url='/api/web/login/')
def dashboard(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user)
    totals = transactions.aggregate(
        income_total=Sum('amount', filter=Q(type='income')),
        expense_total=Sum('amount', filter=Q(type='expense')),
    )
    income_total = totals['income_total'] or Decimal('0')
    expense_total = totals['expense_total'] or Decimal('0')
    net_amount = income_total - expense_total

    budgets = Budget.objects.filter(user=user).order_by('category')
    budget_warnings = []
    budgets_summary = []
    for budget in budgets:
        limit_amount = budget.limit_amount
        spent_amount = budget.spent_amount
        utilization_pct = int((spent_amount / limit_amount) * 100) if limit_amount > 0 else 0
        budgets_summary.append({
            'category': budget.category,
            'limit_amount': limit_amount,
            'spent_amount': spent_amount,
            'remaining': limit_amount - spent_amount,
            'utilization_pct': utilization_pct,
            'alert_threshold': budget.alert_threshold,
        })
        if limit_amount > 0 and utilization_pct >= budget.alert_threshold:
            budget_warnings.append(
                f"⚠️ Budget alert: {utilization_pct}% of {budget.category} budget used (₹{spent_amount}/₹{limit_amount})"
            )

    recent_transactions = transactions.order_by('-date')[:5]

    last_30_days = timezone.now() - timedelta(days=29)
    daily_expenses = (
        transactions
        .filter(type='expense', date__gte=last_30_days)
        .annotate(day=TruncDate('date'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )
    trend_labels = [entry['day'].strftime('%b %d') for entry in daily_expenses]
    trend_values = [float(entry['total']) for entry in daily_expenses]

    breakdown_qs = (
        transactions
        .filter(type='expense')
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:6]
    )
    expense_breakdown = []
    breakdown_labels = []
    breakdown_values = []
    for item in breakdown_qs:
        label = item['category'] or 'Uncategorized'
        amount = item['total'] or Decimal('0')
        expense_breakdown.append({'category': label, 'total': amount})
        breakdown_labels.append(label)
        breakdown_values.append(float(amount))

    context = {
        'income_total': income_total,
        'expense_total': expense_total,
        'net_amount': net_amount,
        'budget_warnings': budget_warnings,
        'budgets_summary': budgets_summary,
        'active_budgets': budgets.count(),
        'recent_transactions': recent_transactions,
        'expense_breakdown': expense_breakdown,
        'has_trend_data': bool(trend_labels),
        'has_breakdown_data': bool(breakdown_labels),
        'trend_labels_json': json.dumps(trend_labels),
        'trend_values_json': json.dumps(trend_values),
        'breakdown_labels_json': json.dumps(breakdown_labels),
        'breakdown_values_json': json.dumps(breakdown_values),
        'has_data': budgets.exists() or transactions.exists(),
    }

    return render(request, 'dashboard.html', context)

@login_required(login_url='/api/web/login/')
def budgets_view(request):
    user = request.user
    
    if request.method == 'POST':
        category = request.POST.get('category', '').strip()
        if not category:
            messages.error(request, 'Please provide a category name for your budget.')
            return redirect('api:web-budgets')

        try:
            limit_amount = Decimal(request.POST.get('limit_amount', '0'))
            alert_threshold = int(request.POST.get('alert_threshold', '80'))
        except (TypeError, ValueError, InvalidOperation):
            messages.error(request, 'Please provide valid numbers for limit and alert threshold.')
            return redirect('api:web-budgets')

        if limit_amount < 0:
            messages.error(request, 'Budget limit cannot be negative.')
            return redirect('api:web-budgets')

        if not 1 <= alert_threshold <= 100:
            messages.error(request, 'Alert threshold should be between 1 and 100%.')
            return redirect('api:web-budgets')

        budget, created = Budget.objects.get_or_create(
            user=user, category=category,
            defaults={'limit_amount': limit_amount, 'alert_threshold': alert_threshold}
        )
        if not created:
            budget.limit_amount = limit_amount
            budget.alert_threshold = alert_threshold
            budget.save()
        
        messages.success(request, f"Budget '{category}' saved successfully!")
        return redirect('api:web-budgets')
    
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
        if tx_type not in ('expense', 'income'):
            messages.error(request, 'Please choose a valid transaction type.')
            return redirect('api:web-transactions')

        try:
            amount = Decimal(request.POST.get('amount', '0'))
        except (TypeError, ValueError, InvalidOperation):
            messages.error(request, 'Please enter a valid amount.')
            return redirect('api:web-transactions')

        if amount <= 0:
            messages.error(request, 'Amount must be greater than zero.')
            return redirect('api:web-transactions')

        category = (request.POST.get('category') or '').strip()
        if not category:
            messages.error(request, 'Category is required.')
            return redirect('api:web-transactions')

        description = request.POST.get('description', '')

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
                    messages.warning(request, alert_msg)
        
        messages.success(request, 'Transaction added successfully!')
        return redirect('api:web-transactions')
    
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

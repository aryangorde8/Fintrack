import json
import base64
import os
import re
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.conf import settings

from .models import Budget, Transaction, Notification, SavingsGoal

# AI Receipt Scanning
def scan_receipt_with_ai(image_data):
    """
    Scan receipt image using Google Gemini AI to extract transaction data.
    Falls back to a demo mode if API key is not configured.
    """
    try:
        import google.generativeai as genai
        
        # Use API key from Django settings
        api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
        
        if not api_key:
            # Demo mode - return sample data for testing
            return {
                'success': True,
                'demo_mode': True,
                'data': {
                    'amount': '299.00',
                    'category': 'Shopping',
                    'description': 'Demo: Sample transaction from receipt scan',
                    'type': 'expense'
                }
            }
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Create prompt for receipt extraction
        prompt = """Analyze this receipt/transaction screenshot and extract the following information in JSON format:
        {
            "amount": "total amount as a number (e.g., 299.50)",
            "category": "best category guess from: Food, Shopping, Transportation, Entertainment, Utilities, Healthcare, Education, Other",
            "description": "brief description of the transaction/items",
            "type": "expense or income"
        }
        
        If you cannot identify a field, use null. Only return the JSON, nothing else.
        Focus on the TOTAL amount, not individual items."""
        
        # Decode base64 image
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        
        response = model.generate_content([
            prompt,
            {'mime_type': 'image/jpeg', 'data': image_bytes}
        ])
        
        # Parse response
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = re.sub(r'^```json?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
        
        data = json.loads(response_text)
        
        return {
            'success': True,
            'demo_mode': False,
            'data': data
        }
        
    except ImportError:
        return {
            'success': True,
            'demo_mode': True,
            'data': {
                'amount': '150.00',
                'category': 'Food',
                'description': 'Demo mode: Install google-generativeai for AI scanning',
                'type': 'expense'
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@csrf_exempt
@login_required(login_url='/api/web/login/')
def scan_receipt(request):
    """Handle receipt image upload and AI scanning."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        data = json.loads(request.body)
        image_data = data.get('image')
        
        if not image_data:
            return JsonResponse({'success': False, 'error': 'No image provided'})
        
        result = scan_receipt_with_ai(image_data)
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

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
    
    # Debug print
    print(f"DEBUG: trend_labels count = {len(trend_labels)}, breakdown_labels count = {len(breakdown_labels)}")
    print(f"DEBUG: has_trend_data = {bool(trend_labels)}, has_breakdown_data = {bool(breakdown_labels)}")

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


# ============================================
# SAVINGS GOALS VIEWS
# ============================================

@login_required(login_url='/api/web/login/')
def goals_view(request):
    """View and manage savings goals"""
    user = request.user
    
    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        
        if action == 'create':
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, 'Please provide a name for your goal.')
                return redirect('api:web-goals')
            
            try:
                target_amount = Decimal(request.POST.get('target_amount', '0'))
                current_amount = Decimal(request.POST.get('current_amount', '0'))
            except (TypeError, ValueError, InvalidOperation):
                messages.error(request, 'Please provide valid amounts.')
                return redirect('api:web-goals')
            
            icon = request.POST.get('icon', '💰')
            color = request.POST.get('color', '#6366f1')
            deadline = request.POST.get('deadline') or None
            
            SavingsGoal.objects.create(
                user=user,
                name=name,
                target_amount=target_amount,
                current_amount=current_amount,
                icon=icon,
                color=color,
                deadline=deadline
            )
            messages.success(request, f'Goal "{name}" created successfully!')
            
        elif action == 'update':
            goal_id = request.POST.get('goal_id')
            try:
                goal = SavingsGoal.objects.get(id=goal_id, user=user)
                add_amount = Decimal(request.POST.get('add_amount', '0'))
                goal.current_amount += add_amount
                goal.save()
                
                if goal.is_completed:
                    messages.success(request, f'🎉 Congratulations! You\'ve reached your "{goal.name}" goal!')
                else:
                    messages.success(request, f'Added ₹{add_amount} to "{goal.name}"!')
            except (SavingsGoal.DoesNotExist, InvalidOperation):
                messages.error(request, 'Could not update goal.')
                
        elif action == 'delete':
            goal_id = request.POST.get('goal_id')
            try:
                goal = SavingsGoal.objects.get(id=goal_id, user=user)
                goal_name = goal.name
                goal.delete()
                messages.success(request, f'Goal "{goal_name}" deleted.')
            except SavingsGoal.DoesNotExist:
                messages.error(request, 'Goal not found.')
        
        return redirect('api:web-goals')
    
    # GET request - display goals
    goals = SavingsGoal.objects.filter(user=user).order_by('-created_at')
    
    # Calculate totals
    total_target = sum(g.target_amount for g in goals)
    total_saved = sum(g.current_amount for g in goals)
    completed_goals = sum(1 for g in goals if g.is_completed)
    
    # Available icons and colors for the form
    icons = ['💰', '🏠', '🚗', '✈️', '💻', '🎓', '💍', '🏥', '🛡️', '🎁', '🎯', '🏖️', '📱', '🎮', '👶']
    colors = ['#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6']
    
    context = {
        'goals': goals,
        'total_target': total_target,
        'total_saved': total_saved,
        'completed_goals': completed_goals,
        'active_goals': goals.count() - completed_goals,
        'icons': icons,
        'colors': colors,
    }
    
    return render(request, 'goals.html', context)


@login_required(login_url='/api/web/login/')
def get_spending_heatmap(request):
    """API endpoint for spending heatmap data"""
    user = request.user
    
    # Get last 365 days of spending data
    start_date = timezone.now() - timedelta(days=365)
    
    daily_spending = (
        Transaction.objects
        .filter(user=user, type='expense', date__gte=start_date)
        .annotate(day=TruncDate('date'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )
    
    # Convert to format suitable for heatmap
    heatmap_data = {}
    for entry in daily_spending:
        date_str = entry['day'].strftime('%Y-%m-%d')
        heatmap_data[date_str] = float(entry['total'])
    
    return JsonResponse({'data': heatmap_data})


@login_required(login_url='/api/web/login/')  
def get_ai_insights(request):
    """Generate AI-powered financial insights"""
    user = request.user
    insights = []
    
    # Get recent transaction data
    last_30_days = timezone.now() - timedelta(days=30)
    last_60_days = timezone.now() - timedelta(days=60)
    
    recent_expenses = Transaction.objects.filter(
        user=user, type='expense', date__gte=last_30_days
    )
    previous_expenses = Transaction.objects.filter(
        user=user, type='expense', date__gte=last_60_days, date__lt=last_30_days
    )
    
    recent_total = recent_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    previous_total = previous_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Insight 1: Spending trend
    if previous_total > 0:
        change_pct = ((recent_total - previous_total) / previous_total) * 100
        if change_pct > 20:
            insights.append({
                'type': 'warning',
                'icon': '📈',
                'title': 'Spending Spike Detected',
                'message': f'Your spending increased by {abs(change_pct):.0f}% compared to last month. Consider reviewing your expenses.'
            })
        elif change_pct < -10:
            insights.append({
                'type': 'success',
                'icon': '🎉',
                'title': 'Great Savings!',
                'message': f'You\'ve reduced spending by {abs(change_pct):.0f}% this month. Keep it up!'
            })
    
    # Insight 2: Top spending category
    top_category = (
        recent_expenses
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
        .first()
    )
    
    if top_category:
        insights.append({
            'type': 'info',
            'icon': '🎯',
            'title': 'Top Spending Category',
            'message': f'{top_category["category"]} is your biggest expense at ₹{top_category["total"]:,.0f} this month.'
        })
    
    # Insight 3: Budget alerts
    over_budget = Budget.objects.filter(
        user=user,
        spent_amount__gt=F('limit_amount')
    ).count()
    
    if over_budget > 0:
        insights.append({
            'type': 'danger',
            'icon': '⚠️',
            'title': 'Budget Alert',
            'message': f'You\'ve exceeded {over_budget} budget(s) this period. Time to review!'
        })
    
    # Insight 4: Savings tip
    if recent_total > 0:
        daily_avg = recent_total / 30
        insights.append({
            'type': 'tip',
            'icon': '💡',
            'title': 'Daily Spending Average',
            'message': f'You spend ₹{daily_avg:,.0f} per day on average. Cutting ₹{daily_avg * 0.1:,.0f}/day could save ₹{daily_avg * 0.1 * 30:,.0f}/month!'
        })
    
    # Insight 5: Goal progress (if goals exist)
    active_goals = SavingsGoal.objects.filter(user=user, current_amount__lt=F('target_amount'))
    if active_goals.exists():
        closest_goal = min(active_goals, key=lambda g: g.remaining_amount)
        insights.append({
            'type': 'goal',
            'icon': '🎯',
            'title': 'Almost There!',
            'message': f'You\'re ₹{closest_goal.remaining_amount:,.0f} away from your "{closest_goal.name}" goal!'
        })
    
    return JsonResponse({'insights': insights})

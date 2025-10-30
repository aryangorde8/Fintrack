#!/usr/bin/env python3
import os
import django
import sys
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Budget, Transaction, Notification

def get_or_create_user():
    """Get or create a user"""
    print("\n=== USER LOGIN/REGISTER ===")
    username = input("Enter username: ").strip()
    
    try:
        user = User.objects.get(username=username)
        print(f"✓ Welcome back, {username}!")
        return user
    except User.DoesNotExist:
        print(f"User '{username}' not found. Creating new user...")
        email = input("Enter email: ").strip()
        password = input("Enter password: ").strip()
        user = User.objects.create_user(username=username, email=email, password=password)
        print(f"✓ User '{username}' created successfully!")
        return user

def create_budget(user):
    """Create or update a budget"""
    print("\n=== CREATE/UPDATE BUDGET ===")
    category = input("Budget category (e.g., Food, Transport, Entertainment): ").strip()
    limit_amount = input("Budget limit amount (₹): ").strip()
    alert_threshold = input("Alert threshold % (default 80): ").strip() or "80"
    
    try:
        limit_amount = Decimal(limit_amount)
        alert_threshold = int(alert_threshold)
        
        budget, created = Budget.objects.get_or_create(
            user=user,
            category=category,
            defaults={
                'limit_amount': limit_amount,
                'alert_threshold': alert_threshold,
                'spent_amount': Decimal('0')
            }
        )
        
        if not created:
            budget.limit_amount = limit_amount
            budget.alert_threshold = alert_threshold
            budget.save()
            print(f"✓ Budget '{category}' updated: ₹{limit_amount} (Alert at {alert_threshold}%)")
        else:
            print(f"✓ Budget '{category}' created: ₹{limit_amount} (Alert at {alert_threshold}%)")
        
        return budget
    except ValueError:
        print("✗ Invalid input. Please enter valid numbers.")
        return None

def add_transaction(user):
    """Add a transaction"""
    print("\n=== ADD TRANSACTION ===")
    print("Type: 1) Expense  2) Income")
    choice = input("Select (1/2): ").strip()
    
    tx_type = 'expense' if choice == '1' else 'income'
    amount = input("Amount (₹): ").strip()
    category = input("Category: ").strip()
    description = input("Description: ").strip()
    
    try:
        amount = Decimal(amount)
        
        transaction = Transaction.objects.create(
            user=user,
            amount=amount,
            type=tx_type,
            category=category,
            description=description
        )
        
        print(f"✓ {tx_type.capitalize()} of ₹{amount} added to '{category}'")
        
        # Update budget and check alert (USE CASE 1)
        if tx_type == 'expense':
            budget, created = Budget.objects.get_or_create(
                user=user,
                category=category,
                defaults={'limit_amount': Decimal('0'), 'spent_amount': Decimal('0'), 'alert_threshold': 80}
            )
            
            budget.spent_amount += amount
            budget.save()
            
            if budget.limit_amount > 0:
                percentage = (budget.spent_amount / budget.limit_amount) * 100
                print(f"  Budget status: ₹{budget.spent_amount} / ₹{budget.limit_amount} ({int(percentage)}%)")
                
                if percentage >= budget.alert_threshold:
                    notification = Notification.objects.create(
                        user=user,
                        type='budget_alert',
                        message=f'⚠️ Budget alert: {int(percentage)}% of {category} budget used!'
                    )
                    print(f"  🚨 ALERT: {notification.message}")
        
        return transaction
    except ValueError:
        print("✗ Invalid amount. Please enter a valid number.")
        return None

def view_budgets(user):
    """View all budgets"""
    print("\n=== YOUR BUDGETS ===")
    budgets = Budget.objects.filter(user=user)
    
    if not budgets.exists():
        print("No budgets found.")
        return
    
    for budget in budgets:
        percentage = (budget.spent_amount / budget.limit_amount * 100) if budget.limit_amount > 0 else 0
        remaining = budget.limit_amount - budget.spent_amount
        status = "🔴 EXCEEDED" if percentage >= 100 else "🟡 WARNING" if percentage >= budget.alert_threshold else "🟢 OK"
        
        print(f"\n{budget.category}:")
        print(f"  Limit: ₹{budget.limit_amount}")
        print(f"  Spent: ₹{budget.spent_amount}")
        print(f"  Remaining: ₹{remaining}")
        print(f"  Usage: {int(percentage)}% {status}")

def view_transactions(user):
    """View recent transactions"""
    print("\n=== RECENT TRANSACTIONS ===")
    transactions = Transaction.objects.filter(user=user).order_by('-date')[:10]
    
    if not transactions.exists():
        print("No transactions found.")
        return
    
    for tx in transactions:
        symbol = "➖" if tx.type == 'expense' else "➕"
        print(f"{symbol} {tx.date.strftime('%Y-%m-%d %H:%M')} | {tx.category:15} | ₹{tx.amount:8} | {tx.description}")

def generate_report(user):
    """Generate financial report (USE CASE 2)"""
    print("\n=== FINANCIAL REPORT ===")
    
    transactions = Transaction.objects.filter(user=user)
    budgets = Budget.objects.filter(user=user)
    
    income_total = sum(t.amount for t in transactions.filter(type='income'))
    expense_total = sum(t.amount for t in transactions.filter(type='expense'))
    net_amount = income_total - expense_total
    
    print(f"\n📊 SUMMARY:")
    print(f"  Total Income:   ₹{income_total}")
    print(f"  Total Expenses: ₹{expense_total}")
    print(f"  Net Amount:     ₹{net_amount}")
    
    print(f"\n📈 BUDGET ANALYSIS:")
    for budget in budgets:
        if budget.limit_amount > 0:
            percentage = int((budget.spent_amount / budget.limit_amount) * 100)
            print(f"  {budget.category}: {percentage}% utilized (₹{budget.spent_amount}/₹{budget.limit_amount})")

def view_notifications(user):
    """View budget alerts"""
    print("\n=== NOTIFICATIONS ===")
    notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
    
    if not notifications.exists():
        print("No notifications.")
        return
    
    for notif in notifications:
        print(f"🔔 {notif.created_at.strftime('%Y-%m-%d %H:%M')} - {notif.message}")

def export_report(user):
    """Export report to CSV"""
    print("\n=== EXPORT REPORT ===")
    transactions = Transaction.objects.filter(user=user).order_by('date')
    
    filename = f"report_{user.username}.csv"
    
    with open(filename, 'w') as f:
        f.write("Date,Type,Category,Amount,Description\n")
        for tx in transactions:
            f.write(f"{tx.date.strftime('%Y-%m-%d')},{tx.type},{tx.category},{tx.amount},{tx.description}\n")
    
    print(f"✓ Report exported to {filename}")
    print(f"  Location: {os.path.abspath(filename)}")

def main():
    print("=" * 50)
    print("    FINTRACK - Personal Finance Manager")
    print("=" * 50)
    
    user = get_or_create_user()
    
    while True:
        print("\n" + "=" * 50)
        print("MENU:")
        print("1. Create/Update Budget")
        print("2. Add Transaction")
        print("3. View Budgets")
        print("4. View Transactions")
        print("5. Generate Report")
        print("6. View Notifications")
        print("7. Export Report (CSV)")
        print("8. Exit")
        print("=" * 50)
        
        choice = input("\nEnter choice (1-8): ").strip()
        
        if choice == '1':
            create_budget(user)
        elif choice == '2':
            add_transaction(user)
        elif choice == '3':
            view_budgets(user)
        elif choice == '4':
            view_transactions(user)
        elif choice == '5':
            generate_report(user)
        elif choice == '6':
            view_notifications(user)
        elif choice == '7':
            export_report(user)
        elif choice == '8':
            print("\n👋 Goodbye!")
            break
        else:
            print("✗ Invalid choice. Please select 1-8.")

if __name__ == '__main__':
    main()

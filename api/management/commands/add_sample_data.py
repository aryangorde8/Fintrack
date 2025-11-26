from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Budget, Transaction
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
import random


class Command(BaseCommand):
    help = 'Add sample financial data to populate charts and dashboards'

    def handle(self, *args, **kwargs):
        # Get the first user or create demo user
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(username='demo', password='demo123')
            self.stdout.write(self.style.SUCCESS('Created demo user: demo/demo123'))
        
        self.stdout.write(f'Adding data for user: {user.username}')

        # Create budgets
        budgets_data = [
            {'category': 'Food', 'limit_amount': Decimal('5000'), 'alert_threshold': 80},
            {'category': 'Transportation', 'limit_amount': Decimal('3000'), 'alert_threshold': 75},
            {'category': 'Entertainment', 'limit_amount': Decimal('2000'), 'alert_threshold': 70},
            {'category': 'Shopping', 'limit_amount': Decimal('4000'), 'alert_threshold': 80},
            {'category': 'Utilities', 'limit_amount': Decimal('2500'), 'alert_threshold': 90},
        ]

        for budget_data in budgets_data:
            budget, created = Budget.objects.get_or_create(
                user=user,
                category=budget_data['category'],
                defaults={
                    'limit_amount': budget_data['limit_amount'],
                    'alert_threshold': budget_data['alert_threshold'],
                    'spent_amount': Decimal('0')
                }
            )
            if created:
                self.stdout.write(f'✓ Created budget: {budget_data["category"]}')

        # Create transactions for the last 30 days
        categories = ['Food', 'Transportation', 'Entertainment', 'Shopping', 'Utilities']
        
        # Income transactions
        income_data = [
            {'amount': Decimal('50000'), 'description': 'Monthly Salary', 'days_ago': 28},
            {'amount': Decimal('5000'), 'description': 'Freelance Project', 'days_ago': 15},
            {'amount': Decimal('2000'), 'description': 'Bonus', 'days_ago': 5},
        ]

        for income in income_data:
            date = timezone.now() - timedelta(days=income['days_ago'])
            Transaction.objects.create(
                user=user,
                type='income',
                amount=income['amount'],
                category='Salary',
                description=income['description'],
                date=date
            )
        
        self.stdout.write(f'✓ Created {len(income_data)} income transactions')

        # Expense transactions
        expense_transactions = [
            {'category': 'Food', 'amount': Decimal('450'), 'description': 'Grocery shopping', 'days_ago': 2},
            {'category': 'Food', 'amount': Decimal('250'), 'description': 'Restaurant dinner', 'days_ago': 5},
            {'category': 'Food', 'amount': Decimal('150'), 'description': 'Coffee shop', 'days_ago': 7},
            {'category': 'Food', 'amount': Decimal('800'), 'description': 'Monthly groceries', 'days_ago': 10},
            {'category': 'Food', 'amount': Decimal('350'), 'description': 'Food delivery', 'days_ago': 15},
            
            {'category': 'Transportation', 'amount': Decimal('500'), 'description': 'Fuel', 'days_ago': 3},
            {'category': 'Transportation', 'amount': Decimal('200'), 'description': 'Uber rides', 'days_ago': 8},
            {'category': 'Transportation', 'amount': Decimal('1500'), 'description': 'Car maintenance', 'days_ago': 20},
            
            {'category': 'Entertainment', 'amount': Decimal('400'), 'description': 'Movie tickets', 'days_ago': 6},
            {'category': 'Entertainment', 'amount': Decimal('800'), 'description': 'Concert tickets', 'days_ago': 12},
            {'category': 'Entertainment', 'amount': Decimal('300'), 'description': 'Netflix subscription', 'days_ago': 25},
            
            {'category': 'Shopping', 'amount': Decimal('2500'), 'description': 'Clothes shopping', 'days_ago': 4},
            {'category': 'Shopping', 'amount': Decimal('1200'), 'description': 'Electronics', 'days_ago': 18},
            
            {'category': 'Utilities', 'amount': Decimal('1200'), 'description': 'Electricity bill', 'days_ago': 9},
            {'category': 'Utilities', 'amount': Decimal('600'), 'description': 'Internet bill', 'days_ago': 11},
            {'category': 'Utilities', 'amount': Decimal('400'), 'description': 'Water bill', 'days_ago': 14},
        ]

        for expense in expense_transactions:
            date = timezone.now() - timedelta(days=expense['days_ago'])
            transaction = Transaction.objects.create(
                user=user,
                type='expense',
                amount=expense['amount'],
                category=expense['category'],
                description=expense['description'],
                date=date
            )
            
            # Update budget spent amount
            budget = Budget.objects.filter(user=user, category=expense['category']).first()
            if budget:
                budget.spent_amount += expense['amount']
                budget.save()

        self.stdout.write(f'✓ Created {len(expense_transactions)} expense transactions')
        
        # Calculate totals
        total_income = sum(t['amount'] for t in income_data)
        total_expenses = sum(t['amount'] for t in expense_transactions)
        
        self.stdout.write(self.style.SUCCESS('\n=== Sample Data Added Successfully! ==='))
        self.stdout.write(f'Total Income: ₹{total_income}')
        self.stdout.write(f'Total Expenses: ₹{total_expenses}')
        self.stdout.write(f'Net: ₹{total_income - total_expenses}')
        self.stdout.write('\nRefresh your dashboard to see the charts populated with data!')

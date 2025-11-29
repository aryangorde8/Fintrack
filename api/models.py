from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=100)
    limit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    spent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    alert_threshold = models.PositiveIntegerField(default=80)

    class Meta:
        unique_together = ('user', 'category')

    def __str__(self):
        return f'{self.user.username} - {self.category}'


class SavingsGoal(models.Model):
    """Track savings goals with visual progress"""
    ICON_CHOICES = [
        ('🏠', 'House'),
        ('🚗', 'Car'),
        ('✈️', 'Travel'),
        ('💻', 'Tech'),
        ('🎓', 'Education'),
        ('💍', 'Wedding'),
        ('🏥', 'Health'),
        ('🛡️', 'Emergency'),
        ('🎁', 'Gift'),
        ('💰', 'Savings'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_goals')
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    icon = models.CharField(max_length=10, default='💰')
    color = models.CharField(max_length=20, default='#6366f1')  # Accent color for the goal
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def progress_percent(self):
        if self.target_amount <= 0:
            return 0
        return min(100, int((self.current_amount / self.target_amount) * 100))
    
    @property
    def remaining_amount(self):
        return max(0, self.target_amount - self.current_amount)
    
    @property
    def is_completed(self):
        return self.current_amount >= self.target_amount
    
    def __str__(self):
        return f'{self.user.username} - {self.name}'


class Transaction(models.Model):
    TYPE_CHOICES = (('expense', 'expense'), ('income', 'income'))
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return f'{self.type} {self.amount} {self.category}'

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    type = models.CharField(max_length=50, default='budget_alert')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.type} for {self.user.username}'

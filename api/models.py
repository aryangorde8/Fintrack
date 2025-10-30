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

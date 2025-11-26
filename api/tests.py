import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Budget, Transaction, Notification


class BudgetAPITests(APITestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='alice', password='pass12345')
		self.client.force_authenticate(user=self.user)

	def test_create_and_update_budget(self):
		url = reverse('api:budgets')
		payload = {'category': 'Food', 'limit_amount': '500.00', 'alert_threshold': 80}
		response = self.client.post(url, payload, format='json')
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		budget = Budget.objects.get(user=self.user, category='Food')
		self.assertEqual(budget.limit_amount, Decimal('500.00'))

		payload['limit_amount'] = '750.00'
		payload['alert_threshold'] = 70
		response = self.client.post(url, payload, format='json')
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		budget.refresh_from_db()
		self.assertEqual(budget.limit_amount, Decimal('750.00'))
		self.assertEqual(budget.alert_threshold, 70)

	def test_budgets_are_scoped_to_authenticated_user(self):
		Budget.objects.create(user=self.user, category='Travel', limit_amount=200)
		other_user = User.objects.create_user(username='bob', password='secret123')
		Budget.objects.create(user=other_user, category='Travel', limit_amount=900)

		response = self.client.get(reverse('api:budgets'))
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]['category'], 'Travel')


class TransactionAPITests(APITestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='carol', password='pass12345')
		self.client.force_authenticate(user=self.user)
		self.budget = Budget.objects.create(
			user=self.user,
			category='Groceries',
			limit_amount=Decimal('100.00'),
			spent_amount=Decimal('0'),
			alert_threshold=80,
		)

	def test_expense_updates_budget_and_creates_notification(self):
		url = reverse('api:transactions')

		first_expense = {'amount': '50.00', 'type': 'expense', 'category': 'Groceries', 'description': 'Weekly shop'}
		response = self.client.post(url, first_expense, format='json')
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.budget.refresh_from_db()
		self.assertEqual(self.budget.spent_amount, Decimal('50.00'))
		self.assertFalse(Notification.objects.filter(user=self.user).exists())

		second_expense = {'amount': '45.00', 'type': 'expense', 'category': 'Groceries', 'description': 'Top up'}
		response = self.client.post(url, second_expense, format='json')
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.budget.refresh_from_db()
		self.assertEqual(self.budget.spent_amount, Decimal('95.00'))
		self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

	def test_income_does_not_adjust_spent_amount(self):
		url = reverse('api:transactions')
		payload = {'amount': '250.00', 'type': 'income', 'category': 'Salary', 'description': 'Monthly pay'}
		response = self.client.post(url, payload, format='json')
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.budget.refresh_from_db()
		self.assertEqual(self.budget.spent_amount, Decimal('0'))


class ReportSummaryAPITests(APITestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='david', password='pass12345')
		self.client.force_authenticate(user=self.user)
		Budget.objects.create(user=self.user, category='Utilities', limit_amount=Decimal('500.00'), spent_amount=Decimal('120.00'))
		Transaction.objects.create(user=self.user, amount=Decimal('1000.00'), type='income', category='Salary')
		Transaction.objects.create(user=self.user, amount=Decimal('120.00'), type='expense', category='Utilities')

	def test_report_summary_returns_income_expense_and_budget_data(self):
		response = self.client.get(reverse('api:report-summary'))
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		summary = response.data['summary']
		self.assertEqual(Decimal(str(summary['totalIncome'])), Decimal('1000.00'))
		self.assertEqual(Decimal(str(summary['totalExpenses'])), Decimal('120.00'))
		self.assertEqual(Decimal(str(summary['netAmount'])), Decimal('880.00'))

		budget_analysis = response.data['budgetAnalysis']
		self.assertEqual(len(budget_analysis), 1)
		self.assertEqual(budget_analysis[0]['category'], 'Utilities')


class DashboardViewTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='eve', password='pass12345')
		Budget.objects.create(user=self.user, category='Housing', limit_amount=Decimal('1500.00'), spent_amount=Decimal('900.00'), alert_threshold=75)
		Transaction.objects.create(user=self.user, amount=Decimal('3000.00'), type='income', category='Salary')
		Transaction.objects.create(user=self.user, amount=Decimal('900.00'), type='expense', category='Housing')
		self.client = Client()
		self.client.login(username='eve', password='pass12345')

	def test_dashboard_context_contains_chart_flags_and_summary(self):
		response = self.client.get(reverse('api:web-dashboard'))
		self.assertEqual(response.status_code, 200)
		self.assertIn('trend_labels_json', response.context)
		self.assertTrue(response.context['has_trend_data'])
		labels = json.loads(response.context['trend_labels_json'])
		self.assertGreater(len(labels), 0)
		budgets_summary = response.context['budgets_summary']
		self.assertEqual(budgets_summary[0]['category'], 'Housing')

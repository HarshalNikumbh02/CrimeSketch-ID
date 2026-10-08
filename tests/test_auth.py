import os
import unittest
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from utils.mongodb import get_users_collection
from accounts.views import ensure_default_admin


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        ensure_default_admin()

    def test_login_page_renders(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("CrimeSketch-ID", response.content.decode('utf-8'))
        self.assertIn("Academic Disclaimer", response.content.decode('utf-8'))

    def test_login_failure_with_wrong_password(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin',
            'password': 'WrongPassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid username or password", response.content.decode('utf-8'))
        self.assertIsNone(self.client.session.get('user_id'))

    def test_login_success(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin',
            'password': 'Admin@123'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.client.session.get('user_id'))
        self.assertEqual(self.client.session.get('username'), 'admin')

    def test_protected_dashboard_redirects_unauthenticated(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_logout(self):
        self.client.post(reverse('accounts:login'), {
            'username': 'admin',
            'password': 'Admin@123'
        })
        self.assertIsNotNone(self.client.session.get('user_id'))

        response = self.client.get(reverse('accounts:logout'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get('user_id'))

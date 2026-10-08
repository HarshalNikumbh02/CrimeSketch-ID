import os
import io
import unittest
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from PIL import Image
from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from utils.mongodb import get_candidates_collection, get_users_collection
from accounts.views import ensure_default_admin


class CandidateManagementTests(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        ensure_default_admin()
        
        # Log in via credentials to set signed session cookie
        login_resp = self.client.post(reverse('accounts:login'), {
            'username': 'admin',
            'password': 'Admin@123'
        })
        self.assertEqual(login_resp.status_code, 302)

    def test_candidate_list_view(self):
        response = self.client.get(reverse('candidates:list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Reference Candidate Database", response.content.decode('utf-8'))

    def test_candidate_detail_view(self):
        cand_col = get_candidates_collection()
        cand = cand_col.find_one({})
        if not cand:
            self.skipTest("No candidates in database.")
            
        response = self.client.get(reverse('candidates:detail', kwargs={'candidate_id': cand['candidate_id']}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(cand['name'], response.content.decode('utf-8'))
        self.assertIn(cand['candidate_id'], response.content.decode('utf-8'))

    def test_candidate_invalid_image_type(self):
        fake_file = SimpleUploadedFile("document.pdf", b"%PDF-1.4 fake pdf data", content_type="application/pdf")
        response = self.client.post(reverse('candidates:add'), {
            'candidate_id': 'TEST-INVALID-99',
            'name': 'Invalid Test',
            'reference_image': fake_file
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid image format", response.content.decode('utf-8'))

    def test_duplicate_candidate_id(self):
        cand_col = get_candidates_collection()
        existing = cand_col.find_one({})
        if not existing:
            self.skipTest("No existing candidate to test duplicate.")

        img = Image.new('RGB', (100, 100), color='blue')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        uploaded = SimpleUploadedFile("dup.jpg", buf.read(), content_type="image/jpeg")

        response = self.client.post(reverse('candidates:add'), {
            'candidate_id': existing['candidate_id'],
            'name': 'Duplicate Person',
            'reference_image': uploaded
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("already exists in database", response.content.decode('utf-8'))

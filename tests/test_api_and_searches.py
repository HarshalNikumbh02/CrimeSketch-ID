import os
import base64
import unittest
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from utils.mongodb import get_users_collection, get_history_collection
from accounts.views import ensure_default_admin


class SearchAndAPITests(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        ensure_default_admin()
        
        login_resp = self.client.post(reverse('accounts:login'), {
            'username': 'admin',
            'password': 'Admin@123'
        })
        self.assertEqual(login_resp.status_code, 302)

        self.sample_face_path = os.path.join('ml', 'models', 'sample_face.jpg')

    def test_pages_render(self):
        for route_name in ['sketch_search', 'live_camera', 'searches:history', 'analytics:index', 'evaluation:index']:
            res = self.client.get(reverse(route_name))
            self.assertEqual(res.status_code, 200, f"Route {route_name} failed with {res.status_code}")

    def test_api_sketch_search_no_file(self):
        res = self.client.post(reverse('api_sketch_search'), {})
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertFalse(data['success'])

    def test_api_sketch_search_with_sample_image(self):
        if not os.path.exists(self.sample_face_path):
            self.skipTest("Sample face not available.")

        with open(self.sample_face_path, 'rb') as f:
            uploaded = SimpleUploadedFile("sample_query.jpg", f.read(), content_type="image/jpeg")

        res = self.client.post(reverse('api_sketch_search'), {
            'sketch_image': uploaded,
            'metric': 'cosine',
            'top_k': 5
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['faces_detected'], 1)
        self.assertIn('primary_matches', data)
        self.assertIn('timing_breakdown', data)
        self.assertIn('processing_time', data)
        self.assertGreater(data['processing_time'], 0.0)

    def test_api_webcam_analyze(self):
        if not os.path.exists(self.sample_face_path):
            self.skipTest("Sample face not available.")

        with open(self.sample_face_path, 'rb') as f:
            b64_str = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"

        res = self.client.post(reverse('api_webcam_analyze'), {
            'frame': b64_str,
            'metric': 'cosine',
            'top_k': 3
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['faces_detected'], 1)
        self.assertIn('face_results', data)
        self.assertIn('processing_time', data)

    def test_export_history_csv(self):
        res = self.client.get(reverse('searches:export_csv'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv')
        self.assertIn(b'Search ID', res.content)

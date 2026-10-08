import os
import json
from datetime import datetime
import cv2
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.hashers import make_password

from utils.mongodb import (
    get_utc_now,
    get_users_collection,
    get_candidates_collection,
    get_settings_collection,
    init_mongo_indexes
)
from ml.face_detection import detect_faces
from ml.embeddings import extract_face_embedding
from evaluation.evaluator import create_demo_benchmark


class Command(BaseCommand):
    help = 'Seeds MongoDB database with default administrator, demo reference candidates, and benchmark dataset.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing MongoDB indexes..."))
        init_mongo_indexes()

        # 1. Admin User
        users_col = get_users_collection()
        if not users_col.find_one({'username': 'admin'}):
            users_col.insert_one({
                'username': 'admin',
                'password': make_password('Admin@123'),
                'email': 'admin@crimesketch.local',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'admin',
                'is_active': True,
                'created_at': get_utc_now(),
                'last_login': None
            })
            self.stdout.write(self.style.SUCCESS("Created admin user: 'admin' (password: Admin@123)"))
        else:
            self.stdout.write(self.style.SUCCESS("Admin user 'admin' already exists."))

        # 2. Settings
        settings_col = get_settings_collection()
        settings_col.update_one(
            {'setting_key': 'default_config'},
            {'$set': {
                'top_k': 10,
                'similarity_metric': 'cosine',
                'detection_threshold': 0.45,
                'theme': 'light',
                'updated_at': get_utc_now()
            }},
            upsert=True
        )

        # 3. Demo Candidates
        candidates_col = get_candidates_collection()
        demo_candidates = [
            {
                'candidate_id': 'CAN-001',
                'name': 'Demo Candidate 001',
                'age': 29,
                'gender': 'Female',
                'status': 'Active',
                'filename': 'demo_001.jpg',
                'notes': 'Demo reference subject for similarity benchmarking.'
            },
            {
                'candidate_id': 'CAN-002',
                'name': 'Demo Candidate 002',
                'age': 26,
                'gender': 'Female',
                'status': 'Active',
                'filename': 'demo_002.jpg',
                'notes': 'Demo subject with high-contrast portrait.'
            },
            {
                'candidate_id': 'CAN-003',
                'name': 'Demo Candidate 003',
                'age': 34,
                'gender': 'Male',
                'status': 'Active',
                'filename': 'demo_003.jpg',
                'notes': 'Demo candidate reference subject 003.'
            },
            {
                'candidate_id': 'CAN-004',
                'name': 'Demo Candidate 004',
                'age': 31,
                'gender': 'Male',
                'status': 'Active',
                'filename': 'demo_004.jpg',
                'notes': 'Demo subject with frontal facial orientation.'
            },
            {
                'candidate_id': 'CAN-005',
                'name': 'Demo Candidate 005',
                'age': 27,
                'gender': 'Female',
                'status': 'Active',
                'filename': 'demo_005.jpg',
                'notes': 'Demo subject with clear facial contours.'
            },
            {
                'candidate_id': 'CAN-006',
                'name': 'Demo Candidate 006',
                'age': 38,
                'gender': 'Male',
                'status': 'Active',
                'filename': 'demo_006.jpg',
                'notes': 'Demo candidate reference subject 006.'
            },
        ]

        inserted_count = 0
        for cand in demo_candidates:
            cid = cand['candidate_id']
            full_img_path = os.path.join(settings.MEDIA_ROOT, 'candidates', cand['filename'])

            if not os.path.exists(full_img_path):
                self.stdout.write(self.style.WARNING(f"Image not found for {cid}: {full_img_path}"))
                continue

            existing = candidates_col.find_one({'candidate_id': cid})
            if existing and existing.get('embedding'):
                self.stdout.write(self.style.NOTICE(f"Candidate {cid} already exists with embedding."))
                continue

            # Process face detection & embedding extraction
            det_res = detect_faces(full_img_path, score_threshold=0.40)
            if det_res['faces_count'] == 0:
                self.stdout.write(self.style.WARNING(f"No face detected in {cand['filename']} for {cid}"))
                continue

            face_info = det_res['faces'][0]
            emb_res = extract_face_embedding(full_img_path, face_info=face_info)

            cand_doc = {
                'candidate_id': cid,
                'name': cand['name'],
                'age': cand['age'],
                'gender': cand['gender'],
                'status': cand['status'],
                'reference_image': f"candidates/{cand['filename']}",
                'image_path': full_img_path,
                'embedding': emb_res['embedding'],
                'embedding_dim': emb_res['vector_dim'],
                'notes': cand['notes'],
                'created_at': get_utc_now(),
                'updated_at': get_utc_now()
            }

            candidates_col.update_one({'candidate_id': cid}, {'$set': cand_doc}, upsert=True)
            inserted_count += 1
            self.stdout.write(self.style.SUCCESS(f"Processed and seeded {cid} ({cand['name']}) with {emb_res['vector_dim']}-d embedding."))

        # 4. Generate demo probe sketches for easy user testing
        searches_dir = os.path.join(settings.MEDIA_ROOT, 'searches')
        os.makedirs(searches_dir, exist_ok=True)
        demo_sketch_path = os.path.join(searches_dir, 'sample_sketch_demo.jpg')
        
        sample_img = os.path.join(settings.MEDIA_ROOT, 'candidates', 'demo_001.jpg')
        if os.path.exists(sample_img):
            bgr = cv2.imread(sample_img)
            sketch, _ = cv2.pencilSketch(bgr, sigma_s=60, sigma_r=0.07, shade_factor=0.05)
            cv2.imwrite(demo_sketch_path, sketch)
            self.stdout.write(self.style.SUCCESS(f"Generated sample testing sketch: {demo_sketch_path}"))

        # 5. Initialize evaluation benchmark
        try:
            bench_count = create_demo_benchmark()
            self.stdout.write(self.style.SUCCESS(f"Initialized evaluation benchmark dataset with {bench_count} test items."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Benchmark init notice: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Seeding completed successfully! ({inserted_count} candidates ready in MongoDB)"))

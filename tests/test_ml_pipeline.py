import os
import unittest
import numpy as np
from ml.face_detection import detect_faces, draw_bounding_boxes
from ml.embeddings import extract_face_embedding
from ml.similarity import (
    cosine_similarity,
    euclidean_distance,
    calculate_similarity_and_distance
)
from ml.matching import rank_candidates
from ml.preprocessing import preprocess_sketch


class MLPipelineTests(unittest.TestCase):
    def setUp(self):
        self.sample_face_path = os.path.join('ml', 'models', 'sample_face.jpg')

    def test_face_detection_on_sample(self):
        if not os.path.exists(self.sample_face_path):
            self.skipTest("Sample face image not available.")
            
        res = detect_faces(self.sample_face_path, score_threshold=0.45)
        self.assertTrue(res['success'])
        self.assertGreaterEqual(res['faces_count'], 1)
        self.assertIn('faces', res)
        self.assertIn('detection_time', res)
        self.assertGreater(res['detection_time'], 0.0)

        # Check face attributes
        face = res['faces'][0]
        self.assertEqual(len(face['bbox']), 4)
        self.assertEqual(len(face['landmarks']), 5)
        self.assertGreater(face['confidence'], 0.45)

    def test_face_embedding_extraction(self):
        if not os.path.exists(self.sample_face_path):
            self.skipTest("Sample face image not available.")

        det = detect_faces(self.sample_face_path)
        emb_res = extract_face_embedding(self.sample_face_path, face_info=det['faces'][0])
        self.assertEqual(emb_res['vector_dim'], 128)
        self.assertEqual(len(emb_res['embedding']), 128)
        self.assertGreater(emb_res['embedding_time'], 0.0)

        # Test L2 norm of embedding is unit length (~1.0)
        norm = np.linalg.norm(np.array(emb_res['embedding']))
        self.assertAlmostEqual(norm, 1.0, places=2)

    def test_cosine_similarity_math(self):
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(vec_a, vec_b), 1.0)

        vec_c = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(vec_a, vec_c), 0.0)

        vec_d = [-1.0, 0.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(vec_a, vec_d), -1.0)

    def test_euclidean_distance_math(self):
        vec_a = [0.0, 0.0, 0.0]
        vec_b = [3.0, 4.0, 0.0]
        self.assertAlmostEqual(euclidean_distance(vec_a, vec_b), 5.0)

    def test_similarity_confidence_bands(self):
        # Self vector
        unit_vec = [1.0 / np.sqrt(128)] * 128
        res_self = calculate_similarity_and_distance(unit_vec, unit_vec, metric='cosine')
        self.assertEqual(res_self['similarity_percentage'], 100.0)
        self.assertEqual(res_self['distance'], 0.0)
        self.assertEqual(res_self['confidence'], 'High')

        # Orthogonal vector
        v1 = [1.0] + [0.0] * 127
        v2 = [0.0, 1.0] + [0.0] * 126
        res_ortho = calculate_similarity_and_distance(v1, v2, metric='cosine')
        self.assertEqual(res_ortho['similarity_percentage'], 50.0)
        self.assertEqual(res_ortho['confidence'], 'Low')

    def test_candidate_ranking_engine(self):
        query = [1.0, 0.0] + [0.0] * 126
        candidates = [
            {'candidate_id': 'C1', 'name': 'Identical Direction', 'embedding': [1.0, 0.0] + [0.0] * 126},
            {'candidate_id': 'C2', 'name': 'Perpendicular Direction', 'embedding': [0.0, 1.0] + [0.0] * 126},
            {'candidate_id': 'C3', 'name': 'Intermediate Direction', 'embedding': [0.7071, 0.7071] + [0.0] * 126},
        ]

        ranked = rank_candidates(query, candidates, metric='cosine', top_k=2)
        top = ranked['top_candidates']
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0]['candidate_id'], 'C1')
        self.assertEqual(top[0]['rank'], 1)
        self.assertEqual(top[1]['candidate_id'], 'C3')
        self.assertEqual(top[1]['rank'], 2)
        self.assertGreater(top[0]['similarity'], top[1]['similarity'])
        self.assertGreater(ranked['matching_time'], 0.0)

    def test_sketch_preprocessing(self):
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        enhanced = preprocess_sketch(dummy_img)
        self.assertIsNotNone(enhanced)
        self.assertEqual(enhanced.shape, dummy_img.shape)

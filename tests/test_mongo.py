import unittest
from bson import ObjectId
from datetime import datetime
from utils.mongodb import (
    get_mongo_client,
    get_database,
    check_mongo_connection,
    get_candidates_collection,
    get_history_collection,
    serialize_doc,
    safe_object_id
)


class MongoDatabaseTests(unittest.TestCase):
    def test_connection_health(self):
        ok, msg = check_mongo_connection()
        self.assertTrue(ok, f"MongoDB should be reachable: {msg}")
        self.assertIn("MongoDB", msg)

    def test_database_and_collections(self):
        db = get_database()
        self.assertIsNotNone(db)
        
        cand_col = get_candidates_collection()
        hist_col = get_history_collection()
        self.assertEqual(cand_col.name, 'candidates')
        self.assertEqual(hist_col.name, 'search_history')

    def test_safe_object_id(self):
        valid_id = "507f1f77bcf86cd799439011"
        obj_id = safe_object_id(valid_id)
        self.assertIsInstance(obj_id, ObjectId)
        self.assertEqual(str(obj_id), valid_id)

        invalid_id = "not-an-objectid"
        self.assertIsNone(safe_object_id(invalid_id))
        self.assertIsNone(safe_object_id(None))

    def test_doc_serialization(self):
        test_oid = ObjectId()
        now = datetime(2026, 1, 1, 12, 0, 0)
        doc = {
            '_id': test_oid,
            'name': 'Test',
            'created_at': now,
            'nested': {'sub_id': test_oid}
        }
        serialized = serialize_doc(doc)
        self.assertEqual(serialized['_id'], str(test_oid))
        self.assertEqual(serialized['created_at'], '2026-01-01 12:00:00')
        self.assertEqual(serialized['nested']['sub_id'], str(test_oid))

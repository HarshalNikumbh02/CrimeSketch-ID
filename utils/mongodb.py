import os
import logging
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from django.conf import settings

logger = logging.getLogger(__name__)

_mongo_client = None


def get_utc_now():
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def get_mongo_client() -> MongoClient:
    """
    Return a singleton PyMongo MongoClient instance.
    Uses connection pooling provided by MongoClient automatically.
    """
    global _mongo_client
    if _mongo_client is None:
        if settings.configured:
            uri = getattr(settings, 'MONGODB_URI', os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
        else:
            uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        logger.info(f"Connecting to MongoDB at {uri.split('@')[-1] if '@' in uri else uri}")
        _mongo_client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=5
        )
    return _mongo_client


def get_database():
    """
    Return the CrimeSketch-ID database instance.
    """
    client = get_mongo_client()
    if settings.configured:
        db_name = getattr(settings, 'MONGODB_DATABASE', os.getenv('MONGODB_DATABASE', 'crimesketch_id'))
    else:
        db_name = os.getenv('MONGODB_DATABASE', 'crimesketch_id')
    return client[db_name]


def check_mongo_connection():
    """
    Check if MongoDB server is reachable.
    Returns (True, details) or (False, error_message).
    """
    try:
        client = get_mongo_client()
        info = client.server_info()
        version = info.get('version', 'unknown')
        return True, f"MongoDB v{version} connected successfully."
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection failed: {e}")
        return False, f"MongoDB connection unavailable: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected MongoDB error: {e}")
        return False, f"MongoDB error: {str(e)}"


# Collection accessors
def get_users_collection():
    return get_database()['users']


def get_candidates_collection():
    return get_database()['candidates']


def get_history_collection():
    return get_database()['search_history']


def get_detected_faces_collection():
    return get_database()['detected_faces']


def get_evaluation_collection():
    return get_database()['evaluation_runs']


def get_settings_collection():
    return get_database()['system_settings']


def init_mongo_indexes():
    """
    Create necessary indexes across collections.
    """
    try:
        db = get_database()
        # users
        db.users.create_index([('username', ASCENDING)], unique=True)
        db.users.create_index([('email', ASCENDING)])
        
        # candidates
        db.candidates.create_index([('candidate_id', ASCENDING)], unique=True)
        db.candidates.create_index([('created_at', DESCENDING)])
        db.candidates.create_index([('name', ASCENDING)])
        db.candidates.create_index([('status', ASCENDING)])
        
        # search_history
        db.search_history.create_index([('search_id', ASCENDING)], unique=True)
        db.search_history.create_index([('created_at', DESCENDING)])
        db.search_history.create_index([('search_type', ASCENDING)])
        db.search_history.create_index([('user_id', ASCENDING)])
        
        # detected_faces
        db.detected_faces.create_index([('search_id', ASCENDING)])
        
        # evaluation_runs
        db.evaluation_runs.create_index([('run_id', ASCENDING)], unique=True)
        db.evaluation_runs.create_index([('timestamp', DESCENDING)])
        
        logger.info("MongoDB indexes verified/created.")
        return True
    except Exception as e:
        logger.warning(f"Could not initialize MongoDB indexes: {e}")
        return False


def serialize_doc(doc):
    """
    Recursively serialize MongoDB document for JSON responses, converting ObjectIds
    and datetimes to clean strings.
    """
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        result = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                result[k] = str(v)
            elif isinstance(v, datetime):
                result[k] = v.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(v, (dict, list)):
                result[k] = serialize_doc(v)
            else:
                result[k] = v
        return result
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.strftime("%Y-%m-%d %H:%M:%S")
    return doc


def safe_object_id(id_val):
    """
    Convert string to ObjectId safely or return None if invalid.
    """
    if not id_val:
        return None
    if isinstance(id_val, ObjectId):
        return id_val
    try:
        return ObjectId(str(id_val))
    except Exception:
        return None

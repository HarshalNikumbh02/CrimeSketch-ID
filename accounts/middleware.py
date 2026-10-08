from utils.mongodb import get_users_collection, safe_object_id


class MongoUserMiddleware:
    """
    Middleware that attaches authenticated MongoDB user document to request.mongo_user.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = request.session.get('user_id')
        request.mongo_user = None
        if user_id:
            try:
                users_col = get_users_collection()
                user = users_col.find_one({'_id': safe_object_id(user_id)})
                if user and user.get('is_active', True):
                    request.mongo_user = user
                else:
                    request.session.flush()
            except Exception:
                request.mongo_user = None

        response = self.get_response(request)
        return response

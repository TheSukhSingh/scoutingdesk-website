# core/middleware.py
class DebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("🔥 DJANGO HIT:", request.method, request.path)
        return self.get_response(request)
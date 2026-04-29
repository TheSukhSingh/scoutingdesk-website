from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        user.username = user.email

    def is_open_for_signup(self, request):
        print("🔥 SIGNUP CHECK HIT")
        return True
    
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
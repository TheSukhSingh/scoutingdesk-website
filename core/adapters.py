from allauth.account.adapter import DefaultAccountAdapter

from activation.utils import get_client_ip

class CustomAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        user.username = user.email

    def is_open_for_signup(self, request):
        print("🔥 SIGNUP CHECK HIT")
        return True
    
    def get_client_ip(self, request):
        return get_client_ip(request)
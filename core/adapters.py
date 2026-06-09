from allauth.account.adapter import DefaultAccountAdapter

from activation.utils import get_client_ip
from django.contrib.auth import get_user_model
User = get_user_model()

class CustomAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        user.username = user.email

    def is_open_for_signup(self, request):
        return True

    def get_signup_redirect_url(self, request):
        return "/#packages"
    
    def get_client_ip(self, request):
        return get_client_ip(request)

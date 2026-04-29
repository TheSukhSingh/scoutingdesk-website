from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        user.username = user.email

    def is_open_for_signup(self, request):
        print("🔥 SIGNUP CHECK HIT")
        return True
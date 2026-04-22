from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'is_locked', 'failed_attempts', 'created_at')


from .models import AuthActivity

admin.site.register(AuthActivity)
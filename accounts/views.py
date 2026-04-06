from django.shortcuts import render

# Create your views here.

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Check password match
        if password != confirm_password:
            return render(request, 'accounts/register.html', {
                'error': 'Passwords do not match'
            })

        # Check existing user
        if User.objects.filter(username=username).exists():
            return render(request, 'accounts/register.html', {
                'error': 'User already exists'
            })

        # Create user
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('/')

    return render(request, 'accounts/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'accounts/login.html', {'error': 'Invalid credentials'})

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('/accounts/login/')
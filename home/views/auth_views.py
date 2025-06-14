from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.urls import reverse
from ..forms import CustomUserCreationForm

def homepage(request):
    return render(request, 'index.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.save()
            login(request, user)
            return redirect('dashboard')
        else:
            print("❌ Registration form invalid:", form.errors)
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

class RoleBasedLoginView(LoginView):
    template_name = 'login.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        return response

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_success_url(self):
        user = self.request.user
        role = getattr(user, 'role', None)
        role_redirects = {
            'student': 'student_dashboard',
            'teacher': 'teacher_dashboard',
            'admin': 'admin_dashboard',
        }
        return reverse(role_redirects.get(role, 'dashboard'))
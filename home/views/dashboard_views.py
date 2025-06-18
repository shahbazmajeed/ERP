# views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.urls import reverse
from ..forms import CustomUserCreationForm
# Home page
def homepage(request):
    return render(request, 'index.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Save user to database
            user = form.save(commit=False)
            user.is_active = True  # ensure the user can log in
            user.save()

            print("✅ Registered new user:", user.username, "| Role:", user.role)

            # Log the user in after registration
            login(request, user)

            # Redirect to role-based dashboard
            role = getattr(user, 'role', None)
            if role == 'student':
                return redirect('student_dashboard')
            elif role == 'teacher':
                return redirect('teacher_dashboard')
            elif role == 'hod':
                return redirect('hod_dashboard')
            elif role == 'admin':
                return redirect('admin_dashboard')
            return redirect('dashboard')
        else:
            print("❌ Registration form invalid:", form.errors)
    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {'form': form})


# Role-based login view
class RoleBasedLoginView(LoginView):
    template_name = 'login.html'
    
    def form_valid(self, form):
        user = form.get_user()
        print("✅ Login attempt for:", user)
        print("   - Is active:", user.is_active)
        response = super().form_valid(form)
        print("✅ Authentication passed. Redirecting...")
        return response

    def form_invalid(self, form):
        print("❌ Login failed:", form.errors)
        return super().form_invalid(form)

    def get_success_url(self):
        user = self.request.user
        role = getattr(user, 'role', None)
        print("➡️ User role is:", role)

        role_redirects = {
            'student': 'student_dashboard',
            'teacher': 'teacher_dashboard',
            'admin': 'admin_dashboard',
            'hod': 'hod_dashboard',
        }

        url_name = role_redirects.get(role)
        if url_name:
            return reverse(url_name)
        
        # fallback
        return reverse('dashboard')


# Generic dashboard redirect based on user role
@login_required
def dashboard(request):
    role = getattr(request.user, 'role', None)
    if role == 'student':
        return redirect('student_dashboard')
    elif role == 'teacher':
        return redirect('teacher_dashboard')
    elif role == 'admin':
        return redirect('admin_dashboard')
    return render(request, 'error.html', {'message': 'User role not defined'})

# Role-specific dashboards
@login_required
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')

@login_required
def student_dashboard(request):
    return render(request, 'student_dashboard.html')



@login_required
def hod_dashboard(request):
    return render(request, 'hod_dashboard.html')
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

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

@login_required
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')

@login_required
def student_dashboard(request):
    return render(request, 'student_dashboard.html')

@login_required
def teacher_dashboard(request):
    return render(request, 'teacher_dashboard.html')
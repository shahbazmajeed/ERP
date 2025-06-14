from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
import openpyxl
from ..forms import UploadStudentFileForm
from ..models import Student

@login_required
def upload_students(request):
    if request.user.role != 'admin':
        return render(request, 'error.html', {'message': 'Unauthorized access'})

    if request.method == 'POST':
        form = UploadStudentFileForm(request.POST, request.FILES)
        if form.is_valid():
            # ... (rest of the upload_students implementation)
            pass
    else:
        form = UploadStudentFileForm()
    return render(request, 'upload_students.html', {'form': form})

@login_required
def list_students(request):
    students = Student.objects.all()
    # ... (rest of the list_students implementation)
    return render(request, 'list_students.html', {
        'students': students,
        # ... other context variables
    })
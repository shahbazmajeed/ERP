

# views.py
import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from ..forms import UploadStudentFileForm
from ..models import Student

@login_required
def upload_students(request):
    if request.user.role != 'admin':
        return render(request, 'error.html', {'message': 'Unauthorized access'})

    if request.method == 'POST':
        form = UploadStudentFileForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active

            students_added = 0
            for row in sheet.iter_rows(min_row=2, values_only=True):
                roll_no, npf_number, first_name, last_name, gender, dob, email, phone, address,  course, year, section = row

                # Skip empty rows
                if not roll_no:
                    continue

                # Optional: Skip duplicate roll_number
                if Student.objects.filter(roll_number=roll_no).exists():
                    continue

                student = Student(
                    roll_number = roll_no,
                    npf_number = npf_number,
                    first_name=first_name,
                    last_name=last_name,
                    gender=gender,
                    date_of_birth=dob,
                    email=email,
                    phone_number=phone,
                    address=address,
                    course=course,
                    year=year,
                    section=section,
                )
                student.save()
                students_added += 1

            messages.success(request, f"Successfully uploaded {students_added} students!")
            return redirect('list_students')
    else:
        form = UploadStudentFileForm()

    return render(request, 'upload_students.html', {'form': form})


def list_students(request):
    students = Student.objects.all()

    # Filter values from request
    filter_course = request.GET.get('course', '')
    filter_year = request.GET.get('year', '')
    filter_section = request.GET.get('section', '')
    filter_gender = request.GET.get('gender', '')

    # Apply filters
    if filter_course:
        students = students.filter(course=filter_course)
    if filter_year:
        students = students.filter(year=filter_year)
    if filter_section:
        students = students.filter(section=filter_section)
    if filter_gender:
        students = students.filter(gender=filter_gender)

    # Get distinct values for dropdowns
    courses = Student.objects.values_list('course', flat=True).distinct()
    years = Student.objects.values_list('year', flat=True).distinct()
    sections = Student.objects.values_list('section', flat=True).distinct()

    return render(request, 'list_students.html', {
        'students': students,
        'filter_course': filter_course,
        'filter_year': filter_year,
        'filter_section': filter_section,
        'filter_gender': filter_gender,
        'courses': courses,
        'years': years,
        'sections': sections,
    })

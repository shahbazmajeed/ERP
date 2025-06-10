# views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.urls import reverse
from .forms import CustomUserCreationForm
from .models import CustomUser

# Home page
def homepage(request):
    return render(request, 'index.html')

from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from .models import CustomUser

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
def teacher_dashboard(request):
    return render(request, 'teacher_dashboard.html')

# views.py
import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import UploadStudentFileForm
from .models import Student

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


import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import TimeTableEntry

def upload_timetable(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']

        try:
            df = pd.read_excel(excel_file)

            # Clear existing timetable for that course/year/section if needed
            course = df['Course'].iloc[0]
            year = df['Year'].iloc[0]
            section = df['Section'].iloc[0]

            TimeTableEntry.objects.filter(course=course, year=year, section=section).delete()

            for index, row in df.iterrows():
                for period_num in range(1, 7):
                    subject = row[f'Period {period_num} Subject']
                    teacher = row[f'Period {period_num} Teacher']
                    classroom = row[f'Period {period_num} Classroom']

                    # Skip empty periods (optional)
                    if subject and pd.notna(subject):
                        TimeTableEntry.objects.create(
                            day=row['Day'],
                            period_number=period_num,
                            subject=subject,
                            teacher_name=teacher if pd.notna(teacher) else '',
                            classroom=classroom if pd.notna(classroom) else '',
                            course=row['Course'],
                            year=row['Year'],
                            section=row['Section']
                        )
            messages.success(request, "✅ Timetable uploaded successfully!")
            return redirect('upload_timetable')

        except Exception as e:
            messages.error(request, f"❌ Error uploading timetable: {str(e)}")

    return render(request, 'upload_timetable.html')

from django.db.models import Q
from .models import TimeTableEntry

def list_timetable(request):
    # Get distinct Course / Year / Section for dropdowns
    courses = TimeTableEntry.objects.values_list('course', flat=True).distinct()
    years = TimeTableEntry.objects.values_list('year', flat=True).distinct()
    sections = TimeTableEntry.objects.values_list('section', flat=True).distinct()

    # Read filters
    filter_course = request.GET.get('course', '')
    filter_year = request.GET.get('year', '')
    filter_section = request.GET.get('section', '')

    # Filter queryset
    timetable = TimeTableEntry.objects.all()

    if filter_course:
        timetable = timetable.filter(course=filter_course)
    if filter_year:
        timetable = timetable.filter(year=filter_year)
    if filter_section:
        timetable = timetable.filter(section=filter_section)

    # Sort by Day and Period Number
    timetable = timetable.order_by('day', 'period_number')

    context = {
        'courses': courses,
        'years': years,
        'sections': sections,
        'filter_course': filter_course,
        'filter_year': filter_year,
        'filter_section': filter_section,
        'timetable': timetable,
    }
    return render(request, 'list_timetable.html', context)

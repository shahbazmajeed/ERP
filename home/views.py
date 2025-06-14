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

import pandas as pd
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import TimeTableEntry, Subject  # Ensure Subject is imported
import re

def parse_subject(subject_text):
    """Extract subject_name and subject_code from string like 'Mathematics (MATH101)'"""
    match = re.match(r'^(.*?)\s*\((.*?)\)$', subject_text.strip())
    if match:
        subject_name, subject_code = match.groups()
        return subject_name.strip(), subject_code.strip()
    else:
        return subject_text.strip(), ""

def upload_timetable(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']

        try:
            df = pd.read_excel(excel_file)

            # Get details for deletion
            course = df['Course'].iloc[0]
            year = df['Year'].iloc[0]
            section = df['Section'].iloc[0]

            # Optional: Clear old entries
            TimeTableEntry.objects.filter(course=course, year=year, section=section).delete()

            for index, row in df.iterrows():
                for period_num in range(1, 7):
                    subject_text = row.get(f'Period {period_num} Subject')
                    teacher = row.get(f'Period {period_num} Teacher', '')
                    classroom = row.get(f'Period {period_num} Classroom', '')

                    if subject_text and pd.notna(subject_text):
                        # Parse subject name and code
                        subject_name, subject_code = parse_subject(subject_text)

                        # Get or create Subject model instance
                        subject_obj, _ = Subject.objects.get_or_create(
                            subject_name=subject_name,
                            subject_code=subject_code
                        )

                        # Save timetable entry
                        TimeTableEntry.objects.create(
                            day=row['Day'],
                            period_number=period_num,
                            subject=subject_obj,
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


from django.shortcuts import render, get_object_or_404, redirect
from .models import Student, Subject, Attendance
from datetime import date, timedelta, datetime
import calendar

def select_attendance_options(request):
    if request.method == 'POST':
        course = request.POST['course']
        year = request.POST['year']
        section = request.POST['section']
        subject_id = request.POST['subject']
        return redirect('attendance_calendar', course=course, year=int(year), section=section, subject_id=int(subject_id))

    subjects = Subject.objects.all()
    return render(request, 'attendance_select.html', {'subjects': subjects})

from datetime import date
import calendar

def attendance_calendar(request, course, year, section, subject_id):
    today = date.today()
    month = int(request.GET.get('month', today.month))
    year_val = int(request.GET.get('year', today.year))

    subject = Subject.objects.get(id=subject_id)
    cal = calendar.Calendar()
    month_days = cal.monthdatescalendar(year_val, month)

    attendance_records = Attendance.objects.filter(
        student__course=course,
        student__year=year,
        student__section=section,
        subject=subject,
        date__month=month,
        date__year=year_val
    ).values_list('date', flat=True)

    context = {
        'course': course,
        'year': year,
        'section': section,
        'subject_id': subject_id,
        'today': today,
        'month_days': month_days,
        'selected_month': month,
        'selected_year': year_val,
        'attendance_dates': set(attendance_records),
        'months': range(1, 13),  # January to December
        'years': range(2023, today.year + 2),  # Example: 2023 to 2026
    }

    return render(request, 'attendance_calendar.html', context)
from django.shortcuts import render, get_object_or_404, redirect
from datetime import datetime
from .models import Student, Subject, Attendance



from django.shortcuts import render, redirect
from .models import TimeTableEntry, Subject

def select_attendance_options(request):
    if request.method == 'POST':
        branch = request.POST['branch']
        year = int(request.POST['year'])
        section = request.POST['section']
        subject_id = int(request.POST['subject_id'])

        return redirect('attendance_calendar', course=branch, year=year, section=section, subject_id=subject_id)

    # ✅ Collect values from the existing timetable & subjects
    branches = TimeTableEntry.objects.values_list('course', flat=True).distinct()
    years = TimeTableEntry.objects.values_list('year', flat=True).distinct()
    sections = TimeTableEntry.objects.values_list('section', flat=True).distinct()
    subjects = Subject.objects.all()

    return render(request, 'filter_attendance.html', {
        'branches': branches,
        'years': years,
        'sections': sections,
        'subjects': subjects,
    })





from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from .models import Student, Attendance, Subject
import numpy as np, cv2, json, base64
from datetime import datetime
from home.face_utils import face_app

@csrf_exempt
def take_attendance(request, course, year, section, subject_id, date):
    subject = get_object_or_404(Subject, id=subject_id)
    selected_date = datetime.strptime(date, "%Y-%m-%d").date()
    today = datetime.today().date()
    is_today, is_future = selected_date == today, selected_date > today

    students = Student.objects.filter(course=course, year=year, section=section)
    existing_attendance = {
        a.student_id: a.status for a in Attendance.objects.filter(
            subject=subject, date=selected_date, student__in=students
        )
    }

    for student in students:
        student.attendance_status = existing_attendance.get(student.id, "Absent")

    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            if not image_data:
                return JsonResponse({"error": "Missing image"}, status=400)

            header, encoded = image_data.split(",", 1)
            img_array = np.frombuffer(base64.b64decode(encoded), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            faces = face_app.get(img)

            detected_embeddings = []
            for face in faces:
                emb = face.embedding
                norm = np.linalg.norm(emb)
                if norm != 0:
                    detected_embeddings.append(emb / norm)

            known_embeddings, student_ids, roll_map = [], [], {}
            for student in students:
                for emb_obj in student.embeddings.all():
                    emb = np.frombuffer(emb_obj.embedding, dtype=np.float32)
                    norm = np.linalg.norm(emb)
                    if norm != 0:
                        known_embeddings.append(emb / norm)
                        student_ids.append(student.id)
                        roll_map[student.id] = student.roll_number

            recognized_ids = set()
            threshold = 0.8
            known_embeddings_array = np.array(known_embeddings)

            for emb in detected_embeddings:
                distances = np.linalg.norm(known_embeddings_array - emb, axis=1)
                min_idx = np.argmin(distances)
                if distances[min_idx] < threshold:
                    recognized_ids.add(student_ids[min_idx])

            return JsonResponse({
                "recognized_rolls": [roll_map[sid] for sid in recognized_ids],
                "recognized_count": len(recognized_ids)
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    if request.method == "POST":
        present_ids = set(map(int, request.POST.getlist("present")))
        for student in students:
            Attendance.objects.update_or_create(
                student=student,
                subject=subject,
                date=selected_date,
                defaults={"status": "Present" if student.id in present_ids else "Absent"}
            )

        return render(request, "take_attendance.html", {
            "students": students,
            "course": course,
            "year": year,
            "section": section,
            "subject": subject,
            "date": selected_date,
            "is_future": is_future,
            "attendance_exists": True,
            "existing_attendance": {
                s.id: "Present" if s.id in present_ids else "Absent" for s in students
            },
            "success": True,
        })

    return render(request, "take_attendance.html", {
        "students": students,
        "course": course,
        "year": year,
        "section": section,
        "subject": subject,
        "date": selected_date,
        "is_future": is_future,
        "today": today,
        "is_today": is_today,
        "attendance_exists": bool(existing_attendance),
        "existing_attendance": existing_attendance,
    })


import numpy as np
from .models import FaceEmbedding

def get_embedding_for_student(roll_number):
    try:
        face_obj = FaceEmbedding.objects.get(student__roll_number=roll_number)
        embedding = np.array(face_obj.embedding, dtype=np.float32)
        return embedding
    except FaceEmbedding.DoesNotExist:
        return None
def face_attendance(request):
    return "aaa"

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from .face_utils import train_face_database  # Ensure this exists and is correct

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

from .face_utils import train_face_database  # Adjust if placed elsewhere

@csrf_exempt
def train_face_view(request):
    context = {}
    if request.method == "POST":
        result = train_face_database()
        context.update({
            "success": True,
            "newly_added": result["added"],
            "total_saved": result["total_images"],
            "skipped": result["skipped"],
        })
    return render(request, 'train_face.html', context)


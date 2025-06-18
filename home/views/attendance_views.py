
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from ..models import Student, Subject, Attendance, FaceEmbedding, TimeTableEntry
from datetime import date, datetime
import calendar
import numpy as np, cv2, json, base64
from ..face_utils import train_face_database, face_app  # Ensure this exists and is correct


from datetime import date
import calendar


def attendance_calendar(request, course, year, section, subject_id):
    today = date.today()
    month = int(request.GET.get('month', today.month))
    year_val = int(request.GET.get('year', today.year))

    subject = Subject.objects.get(id=subject_id)
    cal = calendar.Calendar()
    month_days = cal.monthdatescalendar(year_val, month)

    # ✅ Attendance records already taken
    attendance_records = Attendance.objects.filter(
        student__course=course,
        student__year=year,
        student__section=section,
        subject=subject,
        date__month=month,
        date__year=year_val
    ).values_list('date', flat=True)

    # ✅ Get valid weekday names from TimeTable
    timetable_days_qs = TimeTableEntry.objects.filter(
        course=course,
        year=year,
        section=section,
        subject=subject
    ).values_list('day', flat=True).distinct()

    # ✅ Convert weekday names to weekday numbers (0=Mon, ..., 6=Sun)
    day_name_to_num = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    timetable_day_nums = [day_name_to_num[day] for day in timetable_days_qs if day in day_name_to_num]

    # ✅ Allow attendance only on those weekdays
    allowed_dates = {
        d for week in month_days for d in week
        if d.month == month and d.weekday() in timetable_day_nums
    }

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
        'allowed_dates': allowed_dates,
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'years': range(2023, today.year + 2),
    }

    return render(request, 'attendance_calendar.html', context)


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



def get_embedding_for_student(roll_number):
    try:
        face_obj = FaceEmbedding.objects.get(student__roll_number=roll_number)
        embedding = np.array(face_obj.embedding, dtype=np.float32)
        return embedding
    except FaceEmbedding.DoesNotExist:
        return None



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

from django.shortcuts import render
from home.models import Subject, Attendance, Student

def attendance_analysis_form(request):
    courses = ['BCA', 'B.Tech', 'MCA']  # Add your offered courses here
    subjects = Subject.objects.all()

    if request.GET.get('course') and request.GET.get('year') and request.GET.get('section') and request.GET.get('subject_id'):
        course = request.GET['course']
        year = request.GET['year']
        section = request.GET['section']
        subject_id = request.GET['subject_id']

        attendance_data = Attendance.objects.filter(
            student__course=course,
            student__year=year,
            student__section=section,
            subject_id=subject_id
        )

        # Basic aggregation (e.g., total records)
        total_records = attendance_data.count()

        context = {
            'courses': courses,
            'subjects': subjects,
            'attendance_data': attendance_data,
            'total_records': total_records,
        }
    else:
        context = {
            'courses': courses,
            'subjects': subjects,
        }

    return render(request, 'attendance_analysis_form.html', context)

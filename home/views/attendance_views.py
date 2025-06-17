
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from ..models import Student, Subject, Attendance, FaceEmbedding, TimeTableEntry
from datetime import date, datetime
import calendar
import numpy as np, cv2, json, base64
from ..face_utils import train_face_database, face_app  # Ensure this exists and is correct


def select_attendance_options(request):
    if request.method == 'POST':
        course = request.POST['course']
        year = request.POST['year']
        section = request.POST['section']
        subject_id = request.POST['subject']
        return redirect('attendance_calendar', course=course, year=int(year), section=section, subject_id=int(subject_id))

    subjects = Subject.objects.all()
    return render(request, 'attendance_select.html', {'subjects': subjects})


def attendance_calendar(request, course, year, section, subject_id):
    import calendar
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
    selected_month = int(request.GET.get('month', datetime.now().month))  # Defaults to current month
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
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'selected_month': selected_month,  # Ensure this is an integer
        'years': range(2023, today.year + 2),  # Example: 2023 to 2026
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


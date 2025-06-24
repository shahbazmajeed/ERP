
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

    # ✅ Get most recent active timetable for this subject
    current_timetable_qs = TimeTableEntry.objects.filter(
        course=course,
        year=year,
        section=section,
        subject=subject,
        effective_from__lte=today
    ).order_by('-effective_from')

    if not current_timetable_qs.exists():
        timetable_day_nums = []  # No class scheduled
    else:
        active_entry = current_timetable_qs.first()

        # ✅ Check effective_to boundary if exists
        if active_entry.effective_to and active_entry.effective_to < today:
            timetable_day_nums = []  # No valid timetable
        else:
            # ✅ Fetch all day names for this active timetable
            timetable_days = TimeTableEntry.objects.filter(
                course=course,
                year=year,
                section=section,
                subject=subject,
                effective_from=active_entry.effective_from
            ).values_list('day', flat=True).distinct()

            day_name_to_num = {
                'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                'Friday': 4, 'Saturday': 5, 'Sunday': 6
            }
            timetable_day_nums = [day_name_to_num[day] for day in timetable_days if day in day_name_to_num]

    # ✅ Allow attendance only on those weekdays from timetable
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
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse

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

            # Normalize detected face embeddings
            detected_embeddings = []
            for face in faces:
                emb = face.embedding.astype(np.float32)
                norm = np.linalg.norm(emb)
                if norm != 0:
                    detected_embeddings.append(emb / norm)

            # Prepare known embeddings
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
            threshold = 1.2  # updated threshold
            if known_embeddings and detected_embeddings:
                known_embeddings_array = np.array(known_embeddings, dtype=np.float32)
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





from collections import defaultdict
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.timezone import now
from django.db.models import Count, Q
from datetime import datetime, timedelta
from ..models import TimeTableEntry, Attendance, Subject


def get_filtered_options(request):
    course = request.GET.get('course')
    year = request.GET.get('year')
    section = request.GET.get('section')

    filters = {}
    if course:
        filters['course'] = course
    if year:
        filters['year'] = year
    if section:
        filters['section'] = section

    qs = TimeTableEntry.objects.filter(**filters)

    years = sorted(qs.values_list('year', flat=True).distinct())
    sections = sorted(qs.values_list('section', flat=True).distinct())

    subject_ids = qs.values_list('subject_id', flat=True).distinct()
    subjects = Subject.objects.filter(id__in=subject_ids)
    subjects_list = [{'id': s.id, 'name': s.subject_name, 'code': s.subject_code} for s in subjects]

    return JsonResponse({
        'years': years,
        'sections': sections,
        'subjects': subjects_list,
    })


from collections import defaultdict
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.utils.timezone import now
from django.db.models import Q
from datetime import datetime
from ..models import TimeTableEntry, Attendance, Subject
import pandas as pd


def attendance_analysis(request):
    courses = TimeTableEntry.objects.values_list('course', flat=True).distinct()
    years = TimeTableEntry.objects.values_list('year', flat=True).distinct()
    sections = TimeTableEntry.objects.values_list('section', flat=True).distinct()

    course = request.GET.get('course')
    year = request.GET.get('year')
    section = request.GET.get('section')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    subject_id = request.GET.get('subject_id')

    subjects = []
    analysis = []
    attendance_matrix = []
    total_lectures = 0
    date_list = []

    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else None
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else None
    except ValueError:
        from_date = to_date = None

    if course and year and section and from_date and to_date:
        subjects = TimeTableEntry.objects.filter(
            course=course,
            year=year,
            section=section,
            effective_from__lte=to_date
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=from_date)
        ).select_related('subject').values_list(
            'subject_id', 'subject__subject_name', 'subject__subject_code'
        ).distinct()

        if subject_id:
            date_qs = Attendance.objects.filter(
                student__course=course,
                student__year=year,
                student__section=section,
                subject_id=subject_id,
                date__range=(from_date, to_date)
            ).values_list('date', flat=True).distinct().order_by('date')
            date_list = list(date_qs)

            total_lectures = len(date_list)

            students = Attendance.objects.filter(
                student__course=course,
                student__year=year,
                student__section=section,
                subject_id=subject_id,
                date__range=(from_date, to_date)
            ).values('student__roll_number', 'student__first_name', 'student__last_name').distinct()

            # Summary Analysis
            for student in students:
                present_count = Attendance.objects.filter(
                    student__roll_number=student['student__roll_number'],
                    subject_id=subject_id,
                    date__range=(from_date, to_date),
                    status='Present'
                ).count()
                percent = (present_count / total_lectures * 100) if total_lectures else 0
                analysis.append({
                    'roll': student['student__roll_number'],
                    'name': f"{student['student__first_name']} {student['student__last_name']}",
                    'present': present_count,
                    'total': total_lectures,
                    'percent': round(percent, 2)
                })

            # Matrix format
            matrix = defaultdict(lambda: {'name': '', 'roll': '', 'statuses': {}})
            all_attendance = Attendance.objects.filter(
                student__course=course,
                student__year=year,
                student__section=section,
                subject_id=subject_id,
                date__range=(from_date, to_date)
            ).values('student__roll_number', 'student__first_name', 'student__last_name', 'date', 'status')

            for record in all_attendance:
                roll = record['student__roll_number']
                matrix[roll]['name'] = f"{record['student__first_name']} {record['student__last_name']}"
                matrix[roll]['roll'] = roll
                matrix[roll]['statuses'][record['date']] = 'P' if record['status'] == 'Present' else 'A'

            attendance_matrix = list(matrix.values())

            if 'download' in request.GET and analysis:
                # Sheet 1: Summary
                df_summary = pd.DataFrame(analysis)
                df_summary.columns = ['Roll Number', 'Name', 'Lectures Attended', 'Total Lectures', 'Percentage']

                # Add metadata at the top (as extra rows)
                meta_info = [
                    ['Course', course],
                    ['Semester', year],
                    ['Section', section],
                    ['Subject', next((f"{name} ({code})" for (sid, name, code) in subjects if str(sid) == str(subject_id)), 'N/A')],
                    ['Date Range', f"{from_date_str} to {to_date_str}"],
                    [],
                ]
                df_meta = pd.DataFrame(meta_info, columns=["", ""])

                # Sheet 2: Matrix
                matrix_data = []
                for student in attendance_matrix:
                    row = {
                        'Roll Number': student['roll'],
                        'Name': student['name'],
                    }
                    for d in date_list:
                        row[str(d)] = student['statuses'].get(d, '-')
                    matrix_data.append(row)

                df_matrix = pd.DataFrame(matrix_data)

                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename=attendance_report.xlsx'

                with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
                    # Write summary with metadata first
                    df_meta.to_excel(writer, index=False, header=False, sheet_name='Summary')
                    df_summary.to_excel(writer, index=False, sheet_name='Summary', startrow=len(df_meta) + 1)

                    # Write full matrix without metadata
                    df_matrix.to_excel(writer, index=False, sheet_name='Full Attendance')

                return response

    return render(request, 'attendance_analysis_form.html', {
        'courses': courses,
        'years': years,
        'sections': sections,
        'subjects': subjects,
        'analysis': analysis,
        'attendance_matrix': attendance_matrix,
        'date_list': date_list,
        'total_lectures': total_lectures,
    })

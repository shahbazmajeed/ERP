from django.shortcuts import render, get_object_or_404
from datetime import date
import calendar
from django.db.models import Q
from ..models import Student, TimeTableEntry

def student_today_timetable(request):
    context = {}

    if request.method == "POST":
        roll_number = request.POST.get("roll_number")
        today = date.today()
        today_day_name = calendar.day_name[today.weekday()]  # e.g., 'Monday'

        student = get_object_or_404(Student, roll_number=roll_number)

        # Filter relevant entries
        timetable_entries = TimeTableEntry.objects.filter(
            day__iexact=today_day_name.strip(),
            course__iexact=student.course.strip(),
            year=student.year,
            section__iexact=student.section.strip(),
            effective_from__lte=today
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=today)
        ).order_by('period_number')

        context = {
            "student": student,
            "timetable_entries": timetable_entries,
            "today": today,
            "day": today_day_name,
        }

    return render(request, "student_today_timetable.html", context)

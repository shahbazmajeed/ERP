from django.utils import timezone
from datetime import date
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import Employee, TimeTableEntry

from django.contrib.auth.models import AnonymousUser



@login_required
def teacher_dashboard(request):
    print("Inside teacher_dashboard view")
    print("User object:", request.user.email)
    print("Is authenticated?", request.user.is_authenticated)

    if isinstance(request.user, AnonymousUser):
        print("User is not logged in.")
    
    today_date = date.today().strftime("%Y-%m-%d")
    weekday = timezone.now().strftime("%A")

    try:
        teacher = Employee.objects.get(user=request.user)
        print("test",teacher.eid)
        # Filter timetable entries by EID instead of full name
        timetable_entries = TimeTableEntry.objects.filter(
            teacher_name__endswith=f"({teacher.eid})",
            day=weekday
        ).select_related('subject')

        # Also get all subjects assigned to this teacher (by EID) from timetable
        all_entries = TimeTableEntry.objects.filter(
            teacher_name=str(teacher.eid)
        ).select_related('subject').order_by('day', 'period_number')

        context = {
            'teacher': teacher,
            'timetable_entries': timetable_entries,
            'all_entries': all_entries,
            'today': today_date,
        }
        return render(request, 'teacher_dashboard.html', context)

    except Employee.DoesNotExist:
        # ✅ Still pass all expected variables
        context = {
            'teacher': None,
            'timetable_entries': [],
            'all_entries': [],
            'today': today_date,
            'error_message': 'Teacher profile not found.'
        }
        return render(request, 'teacher_dashboard.html', context)

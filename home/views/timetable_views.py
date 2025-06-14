from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
import pandas as pd
import re
from ..models import TimeTableEntry, Subject

def parse_subject(subject_text):
    match = re.match(r'^(.*?)\s*\((.*?)\)$', subject_text.strip())
    if match:
        return match.groups()
    return subject_text.strip(), ""

@login_required
def upload_timetable(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        try:
            # ... (rest of the upload_timetable implementation)
            pass
        except Exception as e:
            messages.error(request, f"❌ Error uploading timetable: {str(e)}")
    return render(request, 'upload_timetable.html')

@login_required
def list_timetable(request):
    # ... (rest of the list_timetable implementation)
    return render(request, 'list_timetable.html')
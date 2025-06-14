from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
import numpy as np, cv2, json, base64
from datetime import datetime
from .models import Student, Attendance, Subject
from .face_utils import face_app

@csrf_exempt
@login_required
def take_attendance(request, course, year, section, subject_id, date):
    # ... (rest of take_attendance implementation)
    return render(request, "take_attendance.html", context)

@login_required
def face_attendance(request):
    return "aaa"

@csrf_exempt
@login_required
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
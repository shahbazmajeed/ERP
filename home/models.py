from django.contrib.auth.models import AbstractUser
from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from datetime import datetime


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('hod', 'Hod'),
        ('director', 'Director'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',  # unique related name
        blank=True,
        help_text='The groups this user belongs to.',
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',  # unique related name
        blank=True,
        help_text='Specific permissions for this user.',
    )


class Student(models.Model):
    roll_number = models.CharField(max_length=10, unique=True)
    npf_number = models.CharField(max_length=10, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(null=True, blank=True, max_length=100)
    gender = models.CharField(null=True, blank=True, max_length=10)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(null=True,max_length=15)
    address = models.TextField(null=True, blank=True)
    course = models.CharField(max_length=100)
    year = models.IntegerField(null=True)
    section = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.roll_number})"

def take_attendance(request, course, year, section, subject_id, date):
    subject = get_object_or_404(Subject, id=subject_id)
    selected_date = datetime.strptime(date, "%Y-%m-%d").date()

    # Filter students by course, year, section
    students = Student.objects.filter(course=course, year=year, section=section)

    if request.method == 'POST':
        present_ids = request.POST.getlist('present')
        for student in students:
            status = "Present" if str(student.id) in present_ids else "Absent"
            Attendance.objects.update_or_create(
                student=student,
                subject=subject,
                date=selected_date,
                defaults={'status': status}
            )
        return redirect('attendance_calendar', course=course, year=year, section=section, subject_id=subject_id)

    return render(request, 'take_attendance.html', {
        'students': students,
        'course': course,
        'year': year,
        'section': section,
        'subject': subject,
        'date': selected_date
    })

class Subject(models.Model):
    subject_name = models.CharField(max_length=100)
    subject_code = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.subject_name} ({self.subject_code})"


from django.db import models
from datetime import timedelta

class TimeTableEntry(models.Model):
    day = models.CharField(max_length=20)
    period_number = models.IntegerField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher_name = models.CharField(max_length=100)
    eid = models.IntegerField(blank=True, null=True)
    classroom = models.CharField(max_length=100, blank=True)
    course = models.CharField(max_length=50)
    year = models.IntegerField()
    section = models.CharField(max_length=10)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Step 1: Find most recent previous timetable for the same slot
        previous_entry = TimeTableEntry.objects.filter(
            day=self.day,
            period_number=self.period_number,
            subject=self.subject,
            course=self.course,
            year=self.year,
            section=self.section,
            effective_to__isnull=True,
            effective_from__lt=self.effective_from,
        ).exclude(pk=self.pk).order_by('-effective_from').first()

        if previous_entry:
            previous_entry.effective_to = self.effective_from - timedelta(days=1)
            previous_entry.save()

        # Step 2: Save current/new timetable entry
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.day} P{self.period_number} - {self.subject} ({self.course} {self.year}-{self.section})"

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=[("Present", "Present"), ("Absent", "Absent")])

    class Meta:
        unique_together = ('student', 'subject', 'date')

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.date} - {self.status}"

class FaceEmbedding(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='embeddings')
    image_name = models.CharField(max_length=255,null=True, blank=True)  # Optional, to identify source image
    embedding = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.roll_number} - {self.image_name}"

# models.py
from django.db import models
from django.contrib.auth.models import User

class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Employee(models.Model):
    POSITION_CHOICES = [
        ('assistant_professor', 'Assistant Professor'),
        ('teacher', 'Teacher'),
        ('hod', 'Head of Department'),
        ('dean', 'Dean'),
        ('director', 'Director'),
        
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    eid = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    designation = models.CharField(max_length=100)
    position_type = models.CharField(max_length=50, choices=POSITION_CHOICES)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_position_type_display()})"

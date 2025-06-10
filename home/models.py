from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('head', 'Head'),
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
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    date_of_birth = models.DateField()
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    course = models.CharField(max_length=100)
    year = models.IntegerField()
    section = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.roll_number})"

# models.py

class TimeTableEntry(models.Model):
    day = models.CharField(max_length=20)
    period_number = models.IntegerField()
    subject = models.CharField(max_length=100)
    teacher_name = models.CharField(max_length=100)
    classroom = models.CharField(max_length=100, blank=True)
    course = models.CharField(max_length=50)
    year = models.IntegerField()
    section = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.day} - Period {self.period_number} - {self.subject} ({self.course} {self.year}-{self.section})"

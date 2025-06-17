# urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import RoleBasedLoginView


urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('register/', views.register, name='register'),
    path('login/', RoleBasedLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('hod_dashboard/', views.hod_dashboard, name='hod_dashboard'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('upload_students/', views.upload_students, name='upload_students'),
    path('students/', views.list_students, name='list_students'),
    path('upload_timetable/', views.upload_timetable, name='upload_timetable'),
    path('list_timetable/', views.list_timetable, name='list_timetable'),
    # urls.py
    path('attendance/take/<str:course>/<int:year>/<str:section>/<int:subject_id>/<str:date>/', views.take_attendance, name='take_attendance'),
    # must come before the one below
    path('attendance/<str:course>/<int:year>/<str:section>/<int:subject_id>/', views.attendance_calendar, name='attendance_calendar'),
    path('attendance/', views.select_attendance_options, name='filter_attendance'),  # this also works
    path('train-face-database/', views.train_face_view, name='train_face'),

    path('upload_employees/', views.upload_employees, name='upload_employees'),
    path('list_employees/', views.list_employees, name='list_employees'),

    
]




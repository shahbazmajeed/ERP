

import pandas as pd
from django.contrib import messages
from django.shortcuts import render, redirect
from ..models import TimeTableEntry, Subject  # Ensure Subject is imported
import re

def parse_subject(subject_text):
    """Extract subject_name and subject_code from string like 'Mathematics (MATH101)'"""
    match = re.match(r'^(.*?)\s*\((.*?)\)$', subject_text.strip())
    if match:
        subject_name, subject_code = match.groups()
        return subject_name.strip(), subject_code.strip()
    else:
        return subject_text.strip(), ""

def upload_timetable(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']

        try:
            df = pd.read_excel(excel_file)

            # Get details for deletion
            course = df['Course'].iloc[0]
            year = df['Year'].iloc[0]
            section = df['Section'].iloc[0]

            # Optional: Clear old entries
            TimeTableEntry.objects.filter(course=course, year=year, section=section).delete()

            for index, row in df.iterrows():
                for period_num in range(1, 7):
                    subject_text = row.get(f'Period {period_num} Subject')
                    teacher = row.get(f'Period {period_num} Teacher', '')
                    classroom = row.get(f'Period {period_num} Classroom', '')

                    if subject_text and pd.notna(subject_text):
                        # Parse subject name and code
                        subject_name, subject_code = parse_subject(subject_text)

                        # Get or create Subject model instance
                        subject_obj, _ = Subject.objects.get_or_create(
                            subject_name=subject_name,
                            subject_code=subject_code
                        )

                        # Save timetable entry
                        TimeTableEntry.objects.create(
                            day=row['Day'],
                            period_number=period_num,
                            subject=subject_obj,
                            teacher_name=teacher if pd.notna(teacher) else '',
                            classroom=classroom if pd.notna(classroom) else '',
                            course=row['Course'],
                            year=row['Year'],
                            section=row['Section']
                        )

            messages.success(request, "✅ Timetable uploaded successfully!")
            return redirect('upload_timetable')

        except Exception as e:
            messages.error(request, f"❌ Error uploading timetable: {str(e)}")

    return render(request, 'upload_timetable.html')







def list_timetable(request):
    # Get distinct Course / Year / Section for dropdowns
    courses = TimeTableEntry.objects.values_list('course', flat=True).distinct()
    years = TimeTableEntry.objects.values_list('year', flat=True).distinct()
    sections = TimeTableEntry.objects.values_list('section', flat=True).distinct()

    # Read filters
    filter_course = request.GET.get('course', '')
    filter_year = request.GET.get('year', '')
    filter_section = request.GET.get('section', '')

    # Filter queryset
    timetable = TimeTableEntry.objects.all()

    if filter_course:
        timetable = timetable.filter(course=filter_course)
    if filter_year:
        timetable = timetable.filter(year=filter_year)
    if filter_section:
        timetable = timetable.filter(section=filter_section)

    # Sort by Day and Period Number
    timetable = timetable.order_by('day', 'period_number')

    context = {
        'courses': courses,
        'years': years,
        'sections': sections,
        'filter_course': filter_course,
        'filter_year': filter_year,
        'filter_section': filter_section,
        'timetable': timetable,
    }
    return render(request, 'list_timetable.html', context)


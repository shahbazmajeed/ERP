import pandas as pd
from django.contrib import messages
from django.shortcuts import render, redirect
from ..models import TimeTableEntry, Subject, Employee
import re
from datetime import date, timedelta

def parse_subject(subject_text):
    match = re.match(r'^(.*?)\s*\((.*?)\)$', str(subject_text).strip())
    if match:
        subject_name, subject_code = match.groups()
        return subject_name.strip(), subject_code.strip()
    else:
        return subject_text.strip(), ""

def extract_eid(teacher_text):
    match = re.search(r'\((\d+)\)', str(teacher_text))
    return match.group(1) if match else None

def upload_timetable(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']

        try:
            df = pd.read_excel(excel_file)

            course = df['Course'].iloc[0]
            year = df['Year'].iloc[0]
            section = df['Section'].iloc[0]
            effective_from = date.today()

            errors = []
            valid_eids = set(Employee.objects.values_list('eid', flat=True))

            for index, row in df.iterrows():
                day = row['Day']

                for period_num in range(1, 7):
                    subject_text = row.get(f'Period {period_num} Subject')
                    teacher_text = row.get(f'Period {period_num} Teacher', '')
                    classroom = row.get(f'Period {period_num} Classroom', '')

                    if subject_text and pd.notna(subject_text):
                        subject_name, subject_code = parse_subject(subject_text)
                        subject_obj, _ = Subject.objects.get_or_create(
                            subject_name=subject_name,
                            subject_code=subject_code
                        )

                        teacher_eid = extract_eid(teacher_text)

                        if teacher_eid and teacher_eid not in valid_eids:
                            errors.append(f"❌ EID '{teacher_eid}' not found for teacher '{teacher_text}' (Day: {day}, Period: {period_num})")
                        elif not teacher_eid:
                            errors.append(f"❌ Invalid teacher format '{teacher_text}' (Day: {day}, Period: {period_num})")

                        # Set effective_to for previous active entry (only one)
                        prev_entry = TimeTableEntry.objects.filter(
                            day=day,
                            period_number=period_num,
                            subject=subject_obj,
                            course=course,
                            year=year,
                            section=section,
                            effective_to__isnull=True
                        ).order_by('-effective_from').first()

                        if prev_entry:
                            prev_entry.effective_to = effective_from - timedelta(days=1)
                            prev_entry.save()

                        TimeTableEntry.objects.create(
                            day=day,
                            period_number=period_num,
                            subject=subject_obj,
                            teacher_name=teacher_text if pd.notna(teacher_text) else '',
                            classroom=classroom if pd.notna(classroom) else '',
                            course=course,
                            year=year,
                            section=section,
                            eid=teacher_eid,
                            effective_from=effective_from
                        )

            if errors:
                for err in errors:
                    messages.warning(request, err)
            else:
                messages.success(request, "✅ Timetable uploaded successfully with version control.")

            return redirect('upload_timetable')

        except Exception as e:
            messages.error(request, f"❌ Error uploading timetable: {str(e)}")

    return render(request, 'upload_timetable.html')

from django.db.models import Max, Q

def list_timetable(request):
    courses = TimeTableEntry.objects.values_list('course', flat=True).distinct()
    years = TimeTableEntry.objects.values_list('year', flat=True).distinct()
    sections = TimeTableEntry.objects.values_list('section', flat=True).distinct()

    filter_course = request.GET.get('course', '')
    filter_year = request.GET.get('year', '')
    filter_section = request.GET.get('section', '')

    # Step 1: Start with all entries (we will filter them)
    timetable_qs = TimeTableEntry.objects.all()

    # Step 2: Apply filters
    if filter_course:
        timetable_qs = timetable_qs.filter(course=filter_course)
    if filter_year:
        timetable_qs = timetable_qs.filter(year=filter_year)
    if filter_section:
        timetable_qs = timetable_qs.filter(section=filter_section)

    # Step 3: Find latest effective_from for each (course, year, section)
    latest_effective = (
        timetable_qs
        .values('course', 'year', 'section')
        .annotate(latest_date=Max('effective_from'))
    )

    # Step 4: Build OR filter to fetch all entries matching the latest `effective_from`
    q_objects = Q()
    for item in latest_effective:
        q_objects |= Q(
            course=item['course'],
            year=item['year'],
            section=item['section'],
            effective_from=item['latest_date']
        )

    # Step 5: Apply the filter
    timetable = timetable_qs.filter(q_objects).order_by('day', 'period_number')

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
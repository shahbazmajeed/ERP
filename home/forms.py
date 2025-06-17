# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role', 'password1', 'password2')

class UploadStudentFileForm(forms.Form):
    file = forms.FileField()
    # forms.py



from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Employee, Student


class UploadEmployeeFileForm(forms.Form):
    file = forms.FileField(label="Select Excel File")


from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Employee, Student


from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Employee, Student

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role', 'password1', 'password2']

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        role = cleaned_data.get('role')

        if not email or not role:
            raise forms.ValidationError("Email and role are required.")

        role = str(role).strip().lower()

        # ❗ Allow first user to register without validation
        from .models import CustomUser
        if CustomUser.objects.count() == 0:
            return cleaned_data  # Bypass checks for first user

        # ✅ Check if email exists in the expected source
        if role == 'student':
            if not Student.objects.filter(user__email=email).exists():
                raise forms.ValidationError("❌ No matching student found with this email.")
        elif role in ['teacher', 'hod', 'admin']:
            if not Employee.objects.filter(user__email=email).exists():
                raise forms.ValidationError("❌ No matching employee found with this email.")
        else:
            raise forms.ValidationError("❌ Invalid role selected.")

        # ❌ Ensure it's not already registered
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("❌ A user with this email already exists.")

        return cleaned_data

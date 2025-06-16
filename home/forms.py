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


# home/forms.py

from django import forms

class UploadEmployeeFileForm(forms.Form):
    file = forms.FileField(label="Select Excel File")

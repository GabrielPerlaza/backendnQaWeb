from django import forms
from django.contrib.auth.models import User
from .models import Project, UserProfile

BASE_INPUT = (
    "w-full px-4 py-3 bg-slate-900 border border-slate-700 "
    "rounded-xl text-white placeholder-slate-500 "
    "focus:outline-none focus:ring-2 focus:ring-blue-500"
)

BASE_TEXTAREA = BASE_INPUT + " resize-none"


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": BASE_INPUT,
                "placeholder": "Nombre"
            }),
            "last_name": forms.TextInput(attrs={
                "class": BASE_INPUT,
                "placeholder": "Apellido"
            }),
            "email": forms.EmailInput(attrs={
                "class": BASE_INPUT,
                "placeholder": "Email"
            }),
        }
    def clean_email(self):
        email = self.cleaned_data.get("email")

        if not email.endswith("@ug.edu.ec"):
            raise forms.ValidationError(
                "Solo se permite correo institucional @ug.edu.ec"
            )
        return email



class ProfileUpdateForm(forms.ModelForm):

    ROLE_CHOICES = [
        ("developer", "Desarrollador"),
        ("tester", "Tester"),
        ("manager", "Manager"),
        ("other", "Otro"),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": BASE_INPUT})
    )

    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": BASE_TEXTAREA,
            "rows": 4,
            "placeholder": "Cuéntanos sobre ti…"
        })
    )

    company = forms.CharField(
        initial="Universidad de Guayaquil",
        required=False,
        widget=forms.TextInput(attrs={
            "class": BASE_INPUT,
            "readonly": "readonly"
        })
    )

    class Meta:
        model = UserProfile
        fields = ["avatar", "bio", "company", "role"]
        widgets = {
            "avatar": forms.FileInput(attrs={
                "class": "text-slate-300",
                "accept": "image/*"
            })
        }



class ProjectUploadForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description", "file"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": BASE_INPUT,
                "placeholder": "Nombre del proyecto"
            }),
            "description": forms.Textarea(attrs={
                "class": BASE_TEXTAREA,
                "rows": 4,
                "tex-color": "text-black",
                "placeholder": "Descripción del proyecto"
            }),
            "file": forms.ClearableFileInput(attrs={
                "class": "text-slate-300"
            }),
        }
        error_messages = {
            "name": {"unique": "Ya existe un proyecto con este nombre."}
}

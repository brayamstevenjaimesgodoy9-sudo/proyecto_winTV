from django import forms
from django.contrib.auth.models import User, Group


class UsuarioForm(forms.ModelForm):
    username = forms.CharField(label='Usuario')
    first_name = forms.CharField(label='Nombres')
    last_name = forms.CharField(label='Apellidos')
    email = forms.EmailField(label='Correo electrónico')

    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Contraseña'
    )

    rol = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        empty_label='Seleccione un rol',
        label='Rol'
    )

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'password',
            'rol',
        ]
class UsuarioEditarForm(forms.ModelForm):
    rol = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        empty_label='Seleccione un rol',
        label='Rol'
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'rol',
        ]
        labels = {
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo electrónico',
        }
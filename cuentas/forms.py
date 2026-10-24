from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

Usuario = get_user_model()


class EstiloBootstrapMixin:
    def aplicar_estilos(self):
        for nombre, campo in self.fields.items():
            clase = "form-check-input" if isinstance(campo.widget, forms.CheckboxInput) else "form-control"
            if self.is_bound and nombre in self.errors:
                clase += " is-invalid"
            campo.widget.attrs["class"] = clase

    def full_clean(self):
        super().full_clean()
        self.aplicar_estilos()


class RegistroForm(EstiloBootstrapMixin, UserCreationForm):
    first_name = forms.CharField(label="Nombres", max_length=150)
    last_name = forms.CharField(label="Apellidos", max_length=150)
    email = forms.EmailField(label="Correo electrónico")
    acepta_datos = forms.BooleanField(
        label="Acepto el tratamiento de mis datos personales (política pendiente de validación).",
        error_messages={"required": "Debes aceptar el tratamiento de datos para registrarte."},
    )

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({"autocomplete": "email", "placeholder": "nombre@correo.com"})
        self.fields["first_name"].widget.attrs.update({"autocomplete": "given-name"})
        self.fields["last_name"].widget.attrs.update({"autocomplete": "family-name"})
        self.fields["password1"].help_text = "Mínimo 8 caracteres; no uses solo números ni una clave común."
        self.fields["password2"].help_text = ""
        self.aplicar_estilos()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.username = self.cleaned_data["email"]
        usuario.email = self.cleaned_data["email"]
        if commit:
            usuario.save()
        return usuario


class IngresoForm(EstiloBootstrapMixin, AuthenticationForm):
    username = forms.CharField(
        label="Correo electrónico o usuario",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username", "placeholder": "nombre@correo.com"}),
    )
    error_messages = {
        "invalid_login": "Correo o contraseña incorrectos. Revisa los datos e inténtalo de nuevo.",
        "inactive": "Esta cuenta está inactiva.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()

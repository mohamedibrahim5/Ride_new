from django import forms
from django.contrib.auth.forms import AuthenticationForm

class PhoneLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Phone Number"
        self.fields["username"].widget.attrs.update({"placeholder": "Phone Number"})

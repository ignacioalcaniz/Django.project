from django import forms


class CheckoutForm(forms.Form):
    cantidad = forms.IntegerField(min_value=1, max_value=100000, initial=1,
                                  widget=forms.NumberInput(attrs={"class": "form-control"}))
    token = forms.CharField(widget=forms.HiddenInput)

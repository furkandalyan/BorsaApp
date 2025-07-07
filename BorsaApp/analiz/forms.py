from django import forms

class HisseForm(forms.Form):
    kod = forms.CharField(
        label='Hisse Kodu',
        max_length=10,
        widget=forms.TextInput(attrs={
            'placeholder': 'Örn: ASELS',
            'class': 'input'
        })
    )

    baslangic_tarihi = forms.DateField(
        label='Yatırım Başlangıç Tarihi',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'input'
        }),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']
    )

from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem, Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'rate']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_rate(self):
        rate = self.cleaned_data['rate']
        if rate < 0:
            raise forms.ValidationError("Rate cannot be negative.")
        return rate


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['product', 'quantity', 'unit', 'rate', 'discount', 'amount']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'unit': forms.Select(choices=InvoiceItem._meta.get_field('unit').choices, attrs={'class': 'form-select'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super(InvoiceItemForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['rate'].initial = self.instance.product.rate
            self.fields['amount'].initial = self.instance.quantity * self.instance.rate * (1 - self.instance.discount / 100)

    def save(self, *args, **kwargs):
        instance = super().save(commit=False)
        instance.rate = self.instance.product.rate
        instance.amount = instance.quantity * instance.rate * (1 - instance.discount / 100)
        return super().save(*args, **kwargs)


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['buyer_name', 'address', 'date', 'transport']  # Removed bill_no

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(InvoiceForm, self).__init__(*args, **kwargs)
        self.fields['buyer_name'].widget = forms.TextInput(attrs={'class': 'form-control'})
        self.fields['date'].widget = forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
        self.fields['transport'].widget = forms.TextInput(attrs={'class': 'form-control', 'style': 'height: 50px;'})
        self.fields['address'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': '2',
            'style': 'height: 50px;'
        })

    def save(self, commit=True):
        invoice = super().save(commit=False)
        if self.request:
            invoice.user = self.request.user
        if commit:
            invoice.save()
        return invoice


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True,
    widgets={
        'product': forms.Select(attrs={'class': 'form-select'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        'unit': forms.Select(choices=InvoiceItem._meta.get_field('unit').choices, attrs={'class': 'form-select'}),
        'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
        'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
        'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
    }
)
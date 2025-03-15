from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout 
from django.contrib.auth.decorators import login_required
from .models import CustomUser, ShopDetails, Product, Invoice, InvoiceItem
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from .forms import ProductForm, InvoiceForm, InvoiceItemFormSet, InvoiceItemForm
from .models import CustomUser, ShopDetails, Product, Invoice, InvoiceItem, InvoiceSequence
import django.forms as forms
from django.forms import inlineformset_factory
from django.contrib import messages
from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from xhtml2pdf import pisa
from io import BytesIO
from decimal import Decimal
# from weasyprint import HTML
import os
from django.conf import settings


# Function to signup
def signup(request):
    if request.method == 'POST':
        email = request.POST['email']
        username = request.POST['username'] 
        password = request.POST['password']
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered. Please choose another one.")
            return redirect('signup')  # redirect back to signup page
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "This username is already registered. Please choose another one.")
            return redirect('signup') 
        
        user = CustomUser.objects.create_user(email=email, username=username, password=password)
        user.backend = 'invoice.backends.EmailOrUsernameBackend'  # custom authentication for backend
        messages.success(request, "Successfully Signup")
        return redirect('login')    # signup successfull login 
    return render(request, 'registration/signup.html') 


# User login
def custom_login(request):
    if request.method == 'POST':
        identifier = request.POST['identifier']
        password = request.POST['password']
        user = authenticate(request, username=identifier, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Successfully Logged and Configure your details")
            return redirect('dashboard')
        else:
            return render(request, 'registration/login.html', {'error': 'Invalid credentials'})
    return render(request, 'registration/login.html')

# Logout function
def logout_view(request):
    logout(request)
    return redirect('login')


#Show account page
@login_required
def shop_details(request):
    if request.method == 'POST':
        shop_details, created = ShopDetails.objects.get_or_create(user=request.user)
        # Update shop_name and address unconditionally becuse of logo auto removal 
        shop_details.shop_name = request.POST['shop_name']
        shop_details.address = request.POST['address']
        # Only update logo if a new file is provided
        if request.FILES.get('logo'):
            shop_details.logo = request.FILES.get('logo')
        shop_details.save()
        return redirect('shop_details')
    shop_details = ShopDetails.objects.filter(user=request.user).first()
    return render(request, 'invoice/shop_details.html', {'shop_details': shop_details})


# Home Page
@login_required
def home(request):
    shop_details = ShopDetails.objects.filter(user=request.user).first()
    return render(request, 'invoice/dashboard.html', {'shop_details': shop_details})

# Products
@login_required
def products_view(request):
    products = Product.objects.filter(user=request.user)
    shop_details = ShopDetails.objects.filter(user=request.user).first()

    if request.method == 'POST':
        if 'delete_product' in request.POST:
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, id=product_id, user=request.user)
            product.delete()
            messages.success(request, "Product deleted successfully.")
            return redirect('products')

        product_id = request.POST.get('product_id', None)
        if product_id:
            product = get_object_or_404(Product, id=product_id, user=request.user)
            form = ProductForm(request.POST, instance=product)
        else:
            form = ProductForm(request.POST)

        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            messages.success(request, "Product saved successfully.")
            return redirect('products')
        else:
            messages.error(request, "Error saving product. Please check the form.")
    else:
        form = ProductForm()

    return render(request, 'invoice/products.html', {
        'products': products,
        'form': form,
        'shop_details': shop_details,
    })
        
# all invoices
@login_required
def all_invoices(request):
    # Handle GET request to display the list of invoices
    invoices = Invoice.objects.filter(user=request.user).order_by('-created_at')
    shop_details = ShopDetails.objects.filter(user=request.user).first()
    
    # if request.method == "POST":
        # if 'delete_invoice' in request.POST:
        #     invoice_id = request.POST.get('invoice_id')
        #     invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
        #     invoice.delete()
        #     messages.success(request, "Invoice deleted successfully.")
        #     return redirect('all_invoices')
        # if 'edit_invoice' in request.POST:
        #     invoice_id = request.POST.get('invoice_id')
        #     if request.POST.get('action') == 'edit':
        #         return redirect('edit_invoice', pk=invoice_id)
            # elif request.POST.get('action') == 'print':
            #     return GeneratePDFInvoiceView.as_view()(request, invoice_id=invoice_id)
    
    # Render the template with the invoice list
    return render(request, 'invoice/invoices.html', {'invoices': invoices,'shop_details': shop_details})
    
 
#  Create and Edit invoice 
@login_required
def invoice_view(request, invoice_id=None):
    shop_details = ShopDetails.objects.filter(user=request.user).first()
    next_bill_no = None

    if invoice_id:
        invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
        extra = 0 if invoice.items.exists() else 1
        InvoiceItemFormSet = inlineformset_factory(
            Invoice, InvoiceItem, form=InvoiceItemForm, extra=extra, can_delete=True,
            widgets={
                'product': forms.Select(attrs={'class': 'form-select'}),
                'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'unit': forms.Select(choices=InvoiceItem._meta.get_field('unit').choices, attrs={'class': 'form-select'}),
                'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
                'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
                'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            }
        )
        invoice_form = InvoiceForm(instance=invoice, request=request)
        formset = InvoiceItemFormSet(instance=invoice)
        mode = 'edit'
    else:
        extra = 1
        InvoiceItemFormSet = inlineformset_factory(
            Invoice, InvoiceItem, form=InvoiceItemForm, extra=extra, can_delete=True,
            widgets={
                'product': forms.Select(attrs={'class': 'form-select'}),
                'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'unit': forms.Select(choices=InvoiceItem._meta.get_field('unit').choices, attrs={'class': 'form-select'}),
                'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
                'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
                'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            }
        )
        invoice_form = InvoiceForm(request=request)
        invoice = Invoice(user=request.user)
        formset = InvoiceItemFormSet(instance=invoice, queryset=InvoiceItem.objects.none())
        mode = 'create'
        # Calculate next bill_no for display
        sequence, _ = InvoiceSequence.objects.get_or_create(pk=1, defaults={'last_used_bill_no': 0})
        next_bill_no = f"INV{(sequence.last_used_bill_no + 1):04d}"

    for form in formset:
        form.fields['product'].queryset = Product.objects.filter(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if invoice_id:
            invoice_form = InvoiceForm(request.POST, instance=invoice, request=request)
            formset = InvoiceItemFormSet(request.POST, instance=invoice)
            mode = 'edit'
        else:
            invoice_form = InvoiceForm(request.POST, request=request)
            invoice = Invoice(user=request.user)
            formset = InvoiceItemFormSet(request.POST, instance=invoice)
            mode = 'create'

        for form in formset:
            form.fields['product'].queryset = Product.objects.filter(user=request.user)

        if action == 'exit':
            return redirect('all_invoices')

        if invoice_form.is_valid() and formset.is_valid():
            if mode == 'create':
                invoice = invoice_form.save(commit=False)
                invoice.user = request.user
                invoice.save() 
                formset.instance = invoice
            else:
                invoice = invoice_form.save()

            formset.save()
            items = invoice.items.all()
            total_quantity = 0
            total_price = 0
            for item in items:
                if item.product:
                    item.rate = item.product.rate
                    item.amount = item.quantity * item.rate * (1 - item.discount / 100)
                    item.save()
                total_quantity += item.quantity
                total_price += item.amount
            invoice.total_quantity = total_quantity
            invoice.total_price = total_price
            invoice.save()

            if action == 'save':
                messages.success(request, f"Invoice {'created' if mode == 'create' else 'updated'} successfully.")
                return redirect('all_invoices')
            else:
                messages.success(request, "Changes saved. You can continue editing.")
                return redirect('invoice_edit', invoice_id=invoice.id)
        else:
            messages.error(request, "Error saving invoice. Please check the form.")

    return render(request, 'invoice/create_invoice.html', {
        'invoice_form': invoice_form,
        'formset': formset,
        'invoice': invoice if invoice_id else None,
        'mode': mode,
        'shop_details': shop_details,
        'next_bill_no': next_bill_no if mode == 'create' else invoice.bill_no,
    })
    
# Get the product rate for invoice 
@login_required
def get_product_rate(request, product_id):
    try:
        product = Product.objects.get(id=product_id, user=request.user)
        return JsonResponse({'rate': float(product.rate)})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
      
# Delete invoice  
@login_required
def delete_invoice(request, id):
    invoice = Invoice.objects.get(id=id)
    messages.success(request, "Invoice deleted successfully.")
    invoice.delete()
    return redirect('all_invoices')

@login_required
def generate_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    items = invoice.items.all()
    shop = ShopDetails.objects.filter(user=invoice.user).first()

    logo_path = os.path.join(settings.MEDIA_ROOT, shop.logo.name) if shop and shop.logo else None
    context = {
        'invoice': invoice,
        'items': items,
        'shop': shop,
        'logo_path': logo_path,
    }

    html_content = render_to_string('invoice_pdf.html', context)

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(
        html_content,
        dest=buffer,
        encoding='utf-8',
        link_callback=lambda uri, rel: os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, "") if uri.startswith(settings.MEDIA_URL) else uri)
    )

    if pisa_status.err:
        return HttpResponse('Error generating PDF: ' + str(pisa_status.err), status=500)

    buffer.seek(0)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice-{invoice.bill_no}-{invoice.buyer_name}.pdf"'
    response.write(pdf)
    return response
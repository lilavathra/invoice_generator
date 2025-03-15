from django.urls import path
from . import views


urlpatterns = [
    path('dashboard/', views.home, name='dashboard'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('shop-details/', views.shop_details, name='shop_details'),
    path('products/', views.products_view, name='products'),
    path('all-invoices/', views.all_invoices, name='all_invoices'),
    path('create_invoice/', views.invoice_view, name='invoice_create'),
    path('edit_invoice/<int:invoice_id>/', views.invoice_view, name='invoice_edit'),
    path('get-product-rate/<int:product_id>/', views.get_product_rate, name='get_product_rate'),
    path('delete_invoice/<int:id>/', views.delete_invoice, name='delete_invoice'),
    path('invoice/<int:invoice_id>/pdf/', views.generate_pdf, name='generate_pdf'),
]
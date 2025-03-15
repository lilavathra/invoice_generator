from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.username


class ShopDetails(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    logo = models.ImageField(upload_to='logo/', blank=True, null=True)
    shop_name = models.CharField(max_length=150)
    address = models.TextField()
    updated_at = models.DateField(auto_now=True)
    
    def __str__(self):
        return self.shop_name


class Product(models.Model):
    user = models.ForeignKey('invoice.CustomUser', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    buyer_name = models.CharField(max_length=150)
    address = models.TextField(null=True)
    bill_no = models.CharField(max_length=50, unique=True, editable=False)  # Keep unique=True
    date = models.DateField(default=timezone.now)
    transport = models.CharField(max_length=100, blank=True, null=True)
    total_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.bill_no:  # Only generate bill_no if not set
            with transaction.atomic():
                sequence, created = InvoiceSequence.objects.get_or_create(pk=1, defaults={'last_used_bill_no': 0})
                next_bill_no = sequence.get_next_bill_number()
                self.bill_no = f"INV{next_bill_no:04d}"  # e.g., INV0001
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.bill_no} for {self.buyer_name}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, choices=[('kg', 'Kilogram'), ('ltr', 'Liter'), ('unit', 'Unit'), ('g', 'Gram')], default='unit')
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.rate = self.product.rate
        self.amount = self.quantity * self.rate * (1 - self.discount / 100)
        super().save(*args, **kwargs)



    
    
class InvoiceSequence(models.Model):
    last_used_bill_no = models.IntegerField(default=0)  # Global sequence starting at 0

    def get_next_bill_number(self):
        with transaction.atomic():
            self.last_used_bill_no += 1
            self.save()
            return self.last_used_bill_no

    def __str__(self):
        return f"Global invoice sequence: {self.last_used_bill_no}"
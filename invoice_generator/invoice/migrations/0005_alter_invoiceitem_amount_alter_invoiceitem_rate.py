# Generated by Django 5.1.7 on 2025-03-13 05:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoice', '0004_remove_invoice_data_remove_invoice_product_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoiceitem',
            name='amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='rate',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]

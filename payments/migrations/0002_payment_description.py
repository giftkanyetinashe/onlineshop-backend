# Generated by Django 5.2.3 on 2025-07-04 14:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='description',
            field=models.CharField(default='Item Purchase', max_length=255),
        ),
    ]

# Generated by Django 2.2.24 on 2021-12-07 02:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0125_auto_20211207_0213'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='problemdata',
            name='custom_checker',
        ),
        migrations.RemoveField(
            model_name='problemdata',
            name='custom_validator',
        ),
    ]

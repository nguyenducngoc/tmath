# Generated by Django 2.2.24 on 2022-02-28 14:04

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0135_organization_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='last_change_name',
            field=models.DateTimeField(default=datetime.datetime(2022, 1, 29, 14, 4, 22, 656180, tzinfo=utc), verbose_name='last change fullname'),
        ),
    ]

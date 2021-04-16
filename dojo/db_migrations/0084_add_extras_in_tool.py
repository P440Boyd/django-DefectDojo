# Generated by Django 2.2.17 on 2021-03-16 09:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dojo', '0083_remove_ipscan'),
    ]

    operations = [
        migrations.AddField(
            model_name='tool_configuration',
            name='extras',
            field=models.CharField(blank=True, help_text='Additional definitions that will be consumed by scanner', max_length=255, null=True),
        ),
    ]
from django.db import migrations

def add_default_ip(apps, schema_editor):
    AllowedIP = apps.get_model('firewall', 'AllowedIP')
    AllowedIP.objects.create(ip_address="127.0.0.1", description="localhost default access")
    AllowedIP.objects.create(ip_address='10.223.112.35', description='Postman test')

class Migration(migrations.Migration):

    dependencies = [
        ('firewall', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_default_ip),
    ]

from django.db import migrations


def crear_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')

    roles = [
        'ADMINISTRADOR',
        'CAJA',
        'VENDEDOR',
        'TECNICO',
        'ALMACEN',
    ]

    for nombre in roles:
        Group.objects.get_or_create(name=nombre)


def eliminar_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')

    roles = [
        'ADMINISTRADOR',
        'CAJA',
        'VENDEDOR',
        'TECNICO',
        'ALMACEN',
    ]

    Group.objects.filter(name__in=roles).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(
            crear_roles,
            eliminar_roles,
        ),
    ]
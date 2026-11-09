import django.db.models.deletion
from django.db import migrations, models


def completar_votos(apps, schema_editor):
    # votos guardados antes de esta migracion (si los hay)
    Voto = apps.get_model("festival", "Voto")
    for voto in Voto.objects.select_related("opcion__votacion__categoria"):
        voto.votacion_id = voto.opcion.votacion_id
        voto.categoria_id = voto.opcion.votacion.categoria_id
        voto.edicion_id = voto.opcion.votacion.categoria.edicion_id
        voto.save(update_fields=["votacion", "categoria", "edicion"])


class Migration(migrations.Migration):

    dependencies = [
        ("festival", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="voto",
            name="edicion",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, related_name="votos",
                to="festival.edicion", verbose_name="edición",
            ),
        ),
        migrations.AddField(
            model_name="voto",
            name="categoria",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, related_name="votos",
                to="festival.categoria", verbose_name="categoría",
            ),
        ),
        migrations.RunPython(completar_votos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="voto",
            name="edicion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="votos",
                to="festival.edicion", verbose_name="edición",
            ),
        ),
        migrations.AlterField(
            model_name="voto",
            name="categoria",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="votos",
                to="festival.categoria", verbose_name="categoría",
            ),
        ),
        migrations.AddConstraint(
            model_name="voto",
            constraint=models.UniqueConstraint(
                fields=("usuario", "edicion", "categoria"), name="voto_unico_usuario_categoria_edicion",
                violation_error_message="Ya registraste un voto en esta categoría.",
            ),
        ),
    ]

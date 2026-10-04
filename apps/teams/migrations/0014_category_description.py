from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0013_categorylink_traininglocation_categorytraining_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="description",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Krátky popis kategórie zobrazovaný v hero sekcii na webe.",
            ),
        ),
    ]

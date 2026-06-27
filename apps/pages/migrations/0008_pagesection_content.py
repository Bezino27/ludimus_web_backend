# Generated manually for custom page section body content.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0007_create_dorast_page_from_pripravka"),
    ]

    operations = [
        migrations.AddField(
            model_name="pagesection",
            name="content",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="pagesection",
            name="config",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Voliteľné nastavenia vo formáte JSON. "
                    'Pre dokumenty napr. {"document_ids": [1, 2, 3]}, '
                    'alebo ručne {"documents": [{"title": "Prihláška", "url": "https://..."}]}. '
                    'Pre odkazy napr. {"link_ids": [1, 4, 7]}, '
                    'alebo ručne {"links": [{"title": "Turnaj", "url": "https://..."}]}. '
                    "Ak zoznam chýba alebo je prázdny, zobrazia sa všetky aktívne položky."
                ),
            ),
        ),
    ]

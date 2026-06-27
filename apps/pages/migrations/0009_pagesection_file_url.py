# Generated manually for practical custom page section links and files.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0008_pagesection_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="pagesection",
            name="url",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Voliteľný odkaz pre sekcie Klubové odkazy alebo Dokumenty. "
                    "Môže byť externá URL alebo interná cesta, napr. /kontakt."
                ),
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="pagesection",
            name="file",
            field=models.FileField(
                blank=True,
                help_text="Voliteľný súbor pre sekciu Dokumenty.",
                null=True,
                upload_to="pages/sections/",
            ),
        ),
    ]

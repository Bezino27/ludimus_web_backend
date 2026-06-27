# Generated manually for custom page hero images and section items.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0009_pagesection_file_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="pagesection",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Voliteľný obrázok/banner pre Hero sekciu.",
                null=True,
                upload_to="pages/sections/images/",
            ),
        ),
        migrations.CreateModel(
            name="PageSectionItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=160)),
                (
                    "url",
                    models.CharField(
                        blank=True,
                        help_text="Používa sa pri sekcii Vlastné odkazy.",
                        max_length=500,
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        blank=True,
                        help_text="Používa sa pri sekcii Dokumenty.",
                        null=True,
                        upload_to="pages/sections/items/",
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="pages.pagesection",
                    ),
                ),
            ],
            options={
                "verbose_name": "Položka sekcie",
                "verbose_name_plural": "Položky sekcií",
                "ordering": ["order", "id"],
            },
        ),
    ]

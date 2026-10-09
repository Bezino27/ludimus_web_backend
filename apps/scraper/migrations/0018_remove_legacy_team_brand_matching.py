from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scraper", "0017_migrate_explicit_team_branding_data"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="szfbteambrand",
            name="unique_szfb_team_brand_match_key_per_club",
        ),
        migrations.RemoveField(
            model_name="szfbteambrand",
            name="display_name",
        ),
        migrations.RemoveField(
            model_name="szfbteambrand",
            name="match_key",
        ),
        migrations.RemoveField(
            model_name="szfbteambrand",
            name="normalized_match_key",
        ),
        migrations.AlterField(
            model_name="szfbteambrand",
            name="team_name",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterModelOptions(
            name="szfbteambrand",
            options={"ordering": ["team_name"]},
        ),
        migrations.AddConstraint(
            model_name="szfbteambrand",
            constraint=models.UniqueConstraint(
                fields=("club", "team_name"),
                name="unique_szfb_team_brand_name_per_club",
            ),
        ),
        migrations.AddConstraint(
            model_name="szfbteambrand",
            constraint=models.UniqueConstraint(
                condition=models.Q(("szfb_competitor_id__isnull", False)),
                fields=("club", "szfb_competitor_id"),
                name="unique_szfb_team_brand_competitor_per_club",
            ),
        ),
        migrations.AddConstraint(
            model_name="szfbteambrand",
            constraint=models.CheckConstraint(
                condition=~models.Q(("id", models.F("branding_source_id"))),
                name="prevent_szfb_team_brand_self_link",
            ),
        ),
    ]

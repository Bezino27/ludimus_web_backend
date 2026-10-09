from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("scraper", "0018_remove_legacy_team_brand_matching"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="szfbteambrand",
            name="unique_szfb_team_brand_name_per_club",
        ),
        migrations.RemoveConstraint(
            model_name="szfbteambrand",
            name="unique_szfb_team_brand_competitor_per_club",
        ),
        migrations.AddField(
            model_name="szfbteambrand",
            name="competition",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="team_brands",
                to="scraper.szfbcompetition",
            ),
        ),
    ]

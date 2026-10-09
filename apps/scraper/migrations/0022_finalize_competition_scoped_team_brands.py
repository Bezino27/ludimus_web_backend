from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("scraper", "0021_deduplicate_competition_scoped_team_brands"),
    ]

    operations = [
        migrations.AlterField(
            model_name="szfbteambrand",
            name="competition",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="team_brands",
                to="scraper.szfbcompetition",
            ),
        ),
        migrations.AddConstraint(
            model_name="szfbteambrand",
            constraint=models.UniqueConstraint(
                fields=("club", "competition", "team_name"),
                name="unique_szfb_team_brand_name_per_competition",
            ),
        ),
        migrations.AddConstraint(
            model_name="szfbteambrand",
            constraint=models.UniqueConstraint(
                condition=models.Q(("szfb_competitor_id__isnull", False)),
                fields=("club", "competition", "szfb_competitor_id"),
                name="unique_szfb_team_brand_competitor_per_competition",
            ),
        ),
    ]

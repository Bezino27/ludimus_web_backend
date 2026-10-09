import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scraper", "0015_szfbteambrand_use_shadow_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="szfbstandingrow",
            name="szfb_competitor_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="szfbteambrand",
            name="branding_source",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="branding_dependents",
                to="scraper.szfbteambrand",
            ),
        ),
        migrations.AddField(
            model_name="szfbteambrand",
            name="szfb_competitor_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="szfbteambrand",
            name="team_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

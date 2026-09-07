from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("scraper", "0008_szfbautosyncconfig"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="szfbstandingrow",
            unique_together={("competition", "team_name")},
        ),
    ]

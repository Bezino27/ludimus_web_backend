from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("polls", "0002_poll_club"),
    ]

    operations = [
        migrations.AddField(
            model_name="polloption",
            name="video_url",
            field=models.URLField(blank=True, default=""),
        ),
    ]

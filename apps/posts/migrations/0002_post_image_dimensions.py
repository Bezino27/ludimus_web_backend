from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("posts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="image_height",
            field=models.PositiveIntegerField(
                blank=True,
                editable=False,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="post",
            name="image_width",
            field=models.PositiveIntegerField(
                blank=True,
                editable=False,
                null=True,
            ),
        ),
    ]

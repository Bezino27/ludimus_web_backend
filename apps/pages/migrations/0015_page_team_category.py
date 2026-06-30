from django.db import migrations, models
import django.db.models.deletion


CATEGORY_SLUGS = {
    "muzi",
    "juniori",
    "dorast",
    "starsi-ziaci",
    "mladsi-ziaci",
    "pripravka",
}


def link_existing_category_pages(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    Category = apps.get_model("teams", "Category")

    for page in Page.objects.filter(page_type="category", slug__in=CATEGORY_SLUGS):
        category = (
            Category.objects.filter(
                club_id=page.club_id,
                slug=page.slug,
                is_active=True,
            )
            .order_by("-season", "id")
            .first()
        )

        if category:
            page.team_category_id = category.id
            page.save(update_fields=["team_category"])


def unlink_category_pages(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    Page.objects.update(team_category=None)


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0011_category_hero_image_category_league_name"),
        ("pages", "0014_pagesectioncontactitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="page",
            name="team_category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pages",
                to="teams.category",
            ),
        ),
        migrations.AlterField(
            model_name="page",
            name="page_type",
            field=models.CharField(
                choices=[
                    ("home", "Domov"),
                    ("about", "O klube"),
                    ("contact", "Kontakt"),
                    ("recruitment", "Nábor / Pridaj sa"),
                    ("category", "Kategória tímu"),
                    ("articles", "Články"),
                    ("custom", "Vlastná stránka"),
                    ("standard", "Štandardná stránka"),
                ],
                default="standard",
                max_length=30,
            ),
        ),
        migrations.RunPython(link_existing_category_pages, unlink_category_pages),
    ]

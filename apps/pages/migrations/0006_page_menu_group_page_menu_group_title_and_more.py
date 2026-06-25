# Generated manually for Page navigation groups.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0005_alter_pagesection_section_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="page",
            name="menu_group",
            field=models.CharField(
                choices=[
                    ("hidden", "Nezobrazovať v menu"),
                    ("main", "Hlavné menu"),
                    ("youth", "Dropdown Mládež"),
                    ("cta", "CTA tlačidlo"),
                    ("footer", "Iba footer"),
                ],
                default="hidden",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="page",
            name="menu_group_title",
            field=models.CharField(blank=True, max_length=120),
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
        migrations.AlterField(
            model_name="pagesection",
            name="section_type",
            field=models.CharField(
                choices=[
                    ("hero", "Hero"),
                    ("top_posts", "Najdôležitejšie novinky"),
                    ("posts", "Články / novinky"),
                    ("matches_overview", "Zápasy + tabuľka"),
                    ("next_match", "Najbližší zápas"),
                    ("recent_matches", "Posledné zápasy"),
                    ("standings", "Tabuľka"),
                    ("leaders", "Lídri sezóny"),
                    ("partners", "Partneri"),
                    ("poll", "Anketa"),
                    ("recruitment", "Nábor"),
                    ("benefits", "Benefity"),
                    ("team_categories", "Kategórie tímov"),
                    ("faq", "Časté otázky"),
                    ("trainings", "Tréningy"),
                    ("links", "Klubové odkazy"),
                    ("contact", "Kontakt"),
                    ("documents", "Dokumenty"),
                    ("gallery", "Galéria"),
                    ("achievements", "Úspechy"),
                    ("custom_text", "Vlastný text"),
                    ("about_overview", "Prehľad o klube s mapou"),
                    ("about_text", "Textová sekcia o klube"),
                    ("famous_players", "Známi hráči / odchovanci"),
                ],
                max_length=50,
            ),
        ),
    ]

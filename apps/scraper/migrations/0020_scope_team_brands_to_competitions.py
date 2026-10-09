from django.db import migrations


def scope_team_brands_to_competitions(apps, schema_editor):
    Brand = apps.get_model("scraper", "SzfbTeamBrand")
    Standing = apps.get_model("scraper", "SzfbStandingRow")
    Watch = apps.get_model("scraper", "SzfbTeamWatch")

    for club_id in (
        Watch.objects.filter(club_id__isnull=False)
        .values_list("club_id", flat=True)
        .distinct()
    ):
        competition_ids = list(
            Watch.objects.filter(club_id=club_id)
            .values_list("competition_id", flat=True)
            .distinct()
            .order_by("competition_id")
        )
        identities = set()
        for team_name, competitor_id, competition_id in Standing.objects.filter(
            competition_id__in=competition_ids
        ).values_list("team_name", "szfb_competitor_id", "competition_id"):
            identities.add((competition_id, team_name, competitor_id))
        for competition_id, team_name, competitor_id in Watch.objects.filter(
            club_id=club_id
        ).values_list("competition_id", "team_name", "competitor_id"):
            identities.add((competition_id, team_name, competitor_id))

        original_brands = list(Brand.objects.filter(club_id=club_id).order_by("id"))
        claimed_ids = set()

        for competition_id, team_name, competitor_id in sorted(
            identities,
            key=lambda item: (item[0], item[1], item[2] or 0),
        ):
            candidates = [
                brand
                for brand in original_brands
                if brand.id not in claimed_ids and brand.team_name == team_name
            ]
            if not candidates and competitor_id is not None:
                candidates = [
                    brand
                    for brand in original_brands
                    if brand.id not in claimed_ids
                    and brand.szfb_competitor_id == competitor_id
                ]

            if candidates:
                brand = candidates[0]
                brand.competition_id = competition_id
                brand.team_name = team_name
                brand.szfb_competitor_id = competitor_id
                brand.save(
                    update_fields=[
                        "competition_id",
                        "team_name",
                        "szfb_competitor_id",
                    ]
                )
                claimed_ids.add(brand.id)
                continue

            visual_source = next(
                (brand for brand in original_brands if brand.team_name == team_name),
                None,
            )
            brand = Brand.objects.create(
                club_id=club_id,
                competition_id=competition_id,
                team_name=team_name,
                szfb_competitor_id=competitor_id,
                logo=visual_source.logo if visual_source else None,
                shadow_color=visual_source.shadow_color if visual_source else None,
                use_shadow_color=(
                    visual_source.use_shadow_color if visual_source else False
                ),
                is_active=visual_source.is_active if visual_source else True,
                branding_source_id=None,
            )
            claimed_ids.add(brand.id)

        unclaimed = [brand for brand in original_brands if brand.id not in claimed_ids]
        for brand in unclaimed:
            available_competition_id = next(
                (
                    competition_id
                    for competition_id in competition_ids
                    if not Brand.objects.filter(
                        club_id=club_id,
                        competition_id=competition_id,
                        team_name=brand.team_name,
                    ).exclude(id=brand.id).exists()
                ),
                None,
            )
            if available_competition_id is None:
                raise RuntimeError(
                    "SzfbTeamBrand sa nedá bezpečne priradiť k súťaži: "
                    f"brand_id={brand.id}, club_id={club_id}"
                )
            brand.competition_id = available_competition_id
            brand.save(update_fields=["competition_id"])

    orphan_ids = list(
        Brand.objects.filter(competition_id__isnull=True).values_list("id", flat=True)
    )
    if orphan_ids:
        raise RuntimeError(
            "SzfbTeamBrand záznamy bez spravovanej súťaže: "
            + ", ".join(str(value) for value in orphan_ids)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("scraper", "0019_prepare_competition_scoped_team_brands"),
    ]

    operations = [
        migrations.RunPython(
            scope_team_brands_to_competitions,
            migrations.RunPython.noop,
        ),
    ]

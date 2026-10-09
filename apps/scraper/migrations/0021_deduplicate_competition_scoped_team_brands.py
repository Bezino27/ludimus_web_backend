from django.db import migrations, models


def _merge_records(Brand, records, preferred_id=None):
    records = list(records)
    if len(records) < 2:
        return records[0] if records else None

    def score(brand):
        return (
            brand.id == preferred_id,
            bool(brand.logo),
            bool(brand.use_shadow_color and brand.shadow_color),
            bool(brand.shadow_color),
            bool(brand.branding_source_id),
            bool(brand.is_active),
            -brand.id,
        )

    canonical = max(records, key=score)
    duplicate_ids = {brand.id for brand in records if brand.id != canonical.id}
    group_ids = duplicate_ids | {canonical.id}

    external_source_id = next(
        (
            brand.branding_source_id
            for brand in sorted(records, key=score, reverse=True)
            if brand.branding_source_id
            and brand.branding_source_id not in group_ids
        ),
        None,
    )
    logo = canonical.logo or next(
        (brand.logo for brand in records if brand.logo),
        None,
    )
    shadow_color = canonical.shadow_color or next(
        (brand.shadow_color for brand in records if brand.shadow_color),
        None,
    )
    competitor_id = canonical.szfb_competitor_id or next(
        (
            brand.szfb_competitor_id
            for brand in records
            if brand.szfb_competitor_id is not None
        ),
        None,
    )

    canonical.logo = logo
    canonical.shadow_color = shadow_color
    canonical.use_shadow_color = bool(
        shadow_color and any(brand.use_shadow_color for brand in records)
    )
    canonical.is_active = any(brand.is_active for brand in records)
    canonical.szfb_competitor_id = competitor_id
    canonical.branding_source_id = external_source_id
    canonical.save(
        update_fields=[
            "logo",
            "shadow_color",
            "use_shadow_color",
            "is_active",
            "szfb_competitor_id",
            "branding_source_id",
        ]
    )

    Brand.objects.filter(branding_source_id__in=duplicate_ids).exclude(
        id__in=group_ids
    ).update(branding_source_id=canonical.id)
    Brand.objects.filter(id__in=duplicate_ids).delete()
    return canonical


def deduplicate_competition_scoped_team_brands(apps, schema_editor):
    Brand = apps.get_model("scraper", "SzfbTeamBrand")
    Standing = apps.get_model("scraper", "SzfbStandingRow")

    duplicate_names = list(
        Brand.objects.values("club_id", "competition_id", "team_name")
        .annotate(record_count=models.Count("id"))
        .filter(record_count__gt=1)
    )
    for group in duplicate_names:
        records = Brand.objects.filter(
            club_id=group["club_id"],
            competition_id=group["competition_id"],
            team_name=group["team_name"],
        ).order_by("id")
        _merge_records(Brand, records)

    duplicate_competitors = list(
        Brand.objects.filter(szfb_competitor_id__isnull=False)
        .values("club_id", "competition_id", "szfb_competitor_id")
        .annotate(record_count=models.Count("id"))
        .filter(record_count__gt=1)
    )
    for group in duplicate_competitors:
        records = list(
            Brand.objects.filter(
                club_id=group["club_id"],
                competition_id=group["competition_id"],
                szfb_competitor_id=group["szfb_competitor_id"],
            ).order_by("id")
        )
        standing_names = set(
            Standing.objects.filter(
                competition_id=group["competition_id"],
                szfb_competitor_id=group["szfb_competitor_id"],
            ).values_list("team_name", flat=True)
        )
        preferred = next(
            (brand for brand in records if brand.team_name in standing_names),
            records[0],
        )
        canonical = _merge_records(Brand, records, preferred_id=preferred.id)
        if preferred.team_name and canonical.team_name != preferred.team_name:
            canonical.team_name = preferred.team_name
            canonical.save(update_fields=["team_name"])

    if Brand.objects.filter(competition_id__isnull=True).exists():
        raise RuntimeError(
            "Niektoré SzfbTeamBrand záznamy stále nemajú priradenú competition."
        )


class Migration(migrations.Migration):

    dependencies = [
        ("scraper", "0020_scope_team_brands_to_competitions"),
    ]

    operations = [
        migrations.RunPython(
            deduplicate_competition_scoped_team_brands,
            migrations.RunPython.noop,
        ),
    ]

import re
import unicodedata

from django.db import migrations


def _normalize(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _legacy_resolve(team_name, brands):
    normalized_name = _normalize(team_name)
    exact = [
        brand
        for brand in brands
        if _normalize(brand.display_name) == normalized_name
    ]
    if len(exact) == 1:
        return exact[0]

    candidates = []
    for brand in brands:
        key = brand.normalized_match_key
        if key and f" {key} " in f" {normalized_name} ":
            candidates.append(brand)
    if not candidates:
        return None
    longest = max(len(brand.normalized_match_key) for brand in candidates)
    winners = [
        brand
        for brand in candidates
        if len(brand.normalized_match_key) == longest
    ]
    return winners[0] if len(winners) == 1 else None


def migrate_legacy_branding(apps, schema_editor):
    Brand = apps.get_model("scraper", "SzfbTeamBrand")
    Standing = apps.get_model("scraper", "SzfbStandingRow")
    Watch = apps.get_model("scraper", "SzfbTeamWatch")

    for club_id in Brand.objects.values_list("club_id", flat=True).distinct():
        brands = list(Brand.objects.filter(club_id=club_id).order_by("id"))
        competition_ids = Watch.objects.filter(club_id=club_id).values_list(
            "competition_id",
            flat=True,
        )
        team_names = list(
            Standing.objects.filter(competition_id__in=competition_ids)
            .order_by("team_name")
            .values_list("team_name", flat=True)
            .distinct()
        )

        active_brands = [brand for brand in brands if brand.is_active]
        assignments = {brand.id: [] for brand in brands}
        for team_name in team_names:
            winner = _legacy_resolve(team_name, active_brands)
            if winner:
                assignments[winner.id].append(team_name)

        used_names = set()
        primary_names = {}
        for brand in brands:
            matches = assignments[brand.id]
            exact = next(
                (
                    name
                    for name in matches
                    if _normalize(name) == _normalize(brand.display_name)
                ),
                None,
            )
            candidates = ([exact] if exact else []) + [
                name for name in matches if name != exact
            ]
            candidates.extend([brand.display_name, brand.match_key])
            team_name = next(
                (
                    name
                    for name in candidates
                    if name and name not in used_names
                ),
                None,
            )
            if not team_name:
                team_name = f"{brand.display_name} (legacy {brand.id})"
            brand.team_name = team_name
            brand.save(update_fields=["team_name"])
            used_names.add(team_name)
            primary_names[brand.id] = team_name

        for brand in brands:
            for team_name in assignments[brand.id]:
                if team_name in used_names or team_name == primary_names[brand.id]:
                    continue
                Brand.objects.create(
                    club_id=club_id,
                    team_name=team_name,
                    branding_source_id=brand.id,
                    is_active=brand.is_active,
                )
                used_names.add(team_name)


class Migration(migrations.Migration):

    dependencies = [
        ("scraper", "0016_explicit_team_branding_links"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_branding, migrations.RunPython.noop),
    ]

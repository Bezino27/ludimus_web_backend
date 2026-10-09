from collections.abc import Iterable

from django.db import IntegrityError, transaction

from apps.scraper.models import SzfbTeamBrand


def delete_team_brand_logo_if_unreferenced(brand: SzfbTeamBrand):
    """Odstráni súbor iba ak ho nepoužíva competition-scoped klon."""
    if not brand.logo:
        return
    logo_name = brand.logo.name
    if SzfbTeamBrand.objects.exclude(pk=brand.pk).filter(logo=logo_name).exists():
        return
    brand.logo.delete(save=False)


def resolve_team_brand(
    team_name: str,
    brands: Iterable[SzfbTeamBrand],
    competition_id: int | None = None,
    szfb_competitor_id: int | None = None,
    szfb_competition_id: int | None = None,
):
    """
    Nájde konkrétnu tímovú identitu bez fuzzy textového matchingu.
    Vyhľadávanie je vždy obmedzené na konkrétnu súťaž. Competitor ID je
    stabilný identifikátor iba v jej rámci; presný názov je bezpečný fallback.
    """
    if not team_name:
        return None

    active_brands = [
        brand
        for brand in brands
        if brand.is_active
        and (competition_id is None or brand.competition_id == competition_id)
        and (
            szfb_competition_id is None
            or brand.competition.szfb_competition_id == szfb_competition_id
        )
    ]
    if szfb_competitor_id is not None:
        id_match = next(
            (
                brand
                for brand in active_brands
                if brand.szfb_competitor_id == szfb_competitor_id
            ),
            None,
        )
        if id_match:
            return id_match

    exact_name_matches = [
        brand for brand in active_brands if brand.team_name == team_name
    ]
    return exact_name_matches[0] if len(exact_name_matches) == 1 else None


def sync_team_brand_identity(club, competition, team_name, szfb_competitor_id=None):
    """Upsertne SZFB identitu bez zásahu do manuálnych vizuálov/linku."""
    if not club or not competition or not team_name:
        return None

    brand = None
    if szfb_competitor_id is not None:
        brand = SzfbTeamBrand.objects.filter(
            club=club,
            competition=competition,
            szfb_competitor_id=szfb_competitor_id,
        ).first()

    if brand is None:
        brand = SzfbTeamBrand.objects.filter(
            club=club,
            competition=competition,
            team_name=team_name,
        ).first()

    if brand is None:
        try:
            with transaction.atomic():
                return SzfbTeamBrand.objects.create(
                    club=club,
                    competition=competition,
                    team_name=team_name,
                    szfb_competitor_id=szfb_competitor_id,
                )
        except IntegrityError:
            if szfb_competitor_id is not None:
                return SzfbTeamBrand.objects.get(
                    club=club,
                    competition=competition,
                    szfb_competitor_id=szfb_competitor_id,
                )
            return SzfbTeamBrand.objects.get(
                club=club,
                competition=competition,
                team_name=team_name,
            )

    changed_fields = []
    if brand.team_name != team_name:
        brand.team_name = team_name
        changed_fields.append("team_name")
    if szfb_competitor_id is not None and brand.szfb_competitor_id is None:
        brand.szfb_competitor_id = szfb_competitor_id
        changed_fields.append("szfb_competitor_id")
    if changed_fields:
        changed_fields.append("updated_at")
        brand.save(update_fields=changed_fields)
    return brand


def get_club_team_brands(club):
    if not club:
        return []

    return list(
        SzfbTeamBrand.objects.filter(
            club=club,
            is_active=True,
        ).select_related(
            "competition",
            "branding_source__competition",
            "branding_source__branding_source",
        ).order_by(
            "-updated_at", "team_name"
        )
    )

from collections.abc import Iterable

from apps.scraper.models import SzfbTeamBrand, normalize_team_match_key


def _contains_match_key(normalized_team_name: str, normalized_match_key: str) -> bool:
    if not normalized_team_name or not normalized_match_key:
        return False

    haystack = f" {normalized_team_name} "
    needle = f" {normalized_match_key} "
    return needle in haystack


def resolve_team_brand(team_name: str, brands: Iterable[SzfbTeamBrand]):
    """
    Nájde persistentný branding tímu podľa názvu zo SZFB.

    Priorita:
    1. presná zhoda normalizovaného display_name,
    2. najdlhší zodpovedajúci match_key,
    3. pri nejednoznačnej zhode rovnakou dĺžkou vráti None.
    """
    normalized_team_name = normalize_team_match_key(team_name)

    if not normalized_team_name:
        return None

    active_brands = [brand for brand in brands if brand.is_active]

    exact_matches = [
        brand
        for brand in active_brands
        if normalize_team_match_key(brand.display_name) == normalized_team_name
    ]

    if len(exact_matches) == 1:
        return exact_matches[0]

    candidates = [
        brand
        for brand in active_brands
        if _contains_match_key(
            normalized_team_name,
            brand.normalized_match_key,
        )
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda brand: len(brand.normalized_match_key),
        reverse=True,
    )

    longest_length = len(candidates[0].normalized_match_key)
    longest_matches = [
        brand
        for brand in candidates
        if len(brand.normalized_match_key) == longest_length
    ]

    if len(longest_matches) != 1:
        return None

    return longest_matches[0]


def get_club_team_brands(club):
    if not club:
        return []

    return list(
        SzfbTeamBrand.objects.filter(
            club=club,
            is_active=True,
        ).order_by("-updated_at", "display_name")
    )

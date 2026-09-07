from apps.teams.models import Category
from apps.teams.revalidation import HOMEPAGE_CATEGORY_SLUG



def _category_paths(queryset):
    slugs = (
        queryset.exclude(slug="")
        .values_list("slug", flat=True)
        .distinct()
    )
    return sorted({f"/kategorie/{slug}" for slug in slugs})


def get_player_revalidation_paths(club_player):
    if not club_player or not getattr(club_player, "pk", None):
        return []

    categories = Category.objects.filter(
        szfb_team_watch__player_stats__club_player=club_player,
    )
    return _category_paths(categories)


def get_competition_revalidation_paths(competition):
    if not competition or not getattr(competition, "pk", None):
        return []

    categories = Category.objects.filter(
        szfb_team_watch__competition=competition,
        szfb_team_watch__is_active=True,
    )
    paths = _category_paths(categories)

    if categories.filter(slug=HOMEPAGE_CATEGORY_SLUG).exists():
        paths.insert(0, "/")

    return paths


def get_watch_revalidation_paths(watch):
    if not watch or not getattr(watch, "pk", None):
        return []

    categories = Category.objects.filter(szfb_team_watch=watch)
    paths = _category_paths(categories)
    if categories.filter(slug=HOMEPAGE_CATEGORY_SLUG).exists():
        paths.insert(0, "/")
    return paths


def get_player_stat_revalidation_paths(player_stat):
    if not player_stat or not getattr(player_stat, "pk", None):
        return []
    if player_stat.club_player_id:
        return get_player_revalidation_paths(player_stat.club_player)
    return get_watch_revalidation_paths(player_stat.watched_team)

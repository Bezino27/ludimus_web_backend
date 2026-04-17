from .models import Category


def get_season_start_year(season: str) -> int:
    return int(season.split("/")[0])


def recalculate_categories_for_club(club, new_season: str) -> None:
    new_start_year = get_season_start_year(new_season)

    categories = Category.objects.filter(club=club)

    for category in categories:
        old_start_year = get_season_start_year(category.season)

        oldest_offset = old_start_year - category.birth_year_from
        youngest_offset = old_start_year - category.birth_year_to

        category.season = new_season
        category.birth_year_from = new_start_year - oldest_offset
        category.birth_year_to = new_start_year - youngest_offset
        category.save(update_fields=["season", "birth_year_from", "birth_year_to"])
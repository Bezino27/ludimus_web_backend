from apps.teams.models import Category


HOMEPAGE_CATEGORY_SLUG = "muzi"


def _category_path(category):
    slug = getattr(category, "slug", "")
    return f"/kategorie/{slug}" if slug else None


def get_category_revalidation_paths(category, old_slug=None):
    paths = [_category_path(category), "/pridaj_sa"]

    if old_slug and old_slug != getattr(category, "slug", ""):
        paths.append(f"/kategorie/{old_slug}")

    if getattr(category, "slug", "") == HOMEPAGE_CATEGORY_SLUG or old_slug == HOMEPAGE_CATEGORY_SLUG:
        paths.append("/")

    return [path for path in paths if path]


def get_category_child_revalidation_paths(category):
    path = _category_path(category)
    return [path] if path else []


def get_training_location_revalidation_paths(location):
    if not location or not getattr(location, "pk", None):
        return []

    slugs = (
        Category.objects.filter(trainings__location=location)
        .exclude(slug="")
        .values_list("slug", flat=True)
        .distinct()
    )
    return sorted({f"/kategorie/{slug}" for slug in slugs})


def get_club_season_revalidation_paths(club_season):
    club = getattr(club_season, "club", None)
    if not club or not getattr(club, "pk", None):
        return []

    slugs = (
        Category.objects.filter(club=club, is_active=True)
        .exclude(slug="")
        .values_list("slug", flat=True)
        .distinct()
    )
    category_paths = {f"/kategorie/{slug}" for slug in slugs}
    return ["/", "/pridaj_sa", *sorted(category_paths)]

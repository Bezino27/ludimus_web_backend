from apps.teams.models import Category


def get_contact_revalidation_paths(_obj=None):
    return ["/kontakt"]


def get_club_link_revalidation_paths(club):
    if not club or not getattr(club, "pk", None):
        return []

    slugs = (
        Category.objects.filter(club=club, is_active=True)
        .exclude(slug="")
        .values_list("slug", flat=True)
        .distinct()
    )
    return sorted({f"/kategorie/{slug}" for slug in slugs})

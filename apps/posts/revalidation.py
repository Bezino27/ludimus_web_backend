from apps.common.revalidation import schedule_revalidation
from apps.teams.models import Category


def get_club_post_category_paths(club):
    if not club or not getattr(club, "pk", None):
        return []

    slugs = (
        Category.objects.filter(club=club, is_active=True)
        .exclude(slug="")
        .values_list("slug", flat=True)
        .distinct()
    )
    return sorted({f"/kategorie/{slug}" for slug in slugs})


def get_post_revalidation_paths(post, old_slug=None):
    paths = ["/", "/clanky", "/sitemap.xml"]

    if getattr(post, "slug", ""):
        paths.append(f"/clanky/{post.slug}")

    if old_slug and old_slug != getattr(post, "slug", ""):
        paths.append(f"/clanky/{old_slug}")

    paths.extend(get_club_post_category_paths(getattr(post, "club", None)))
    return paths


def revalidate_post_paths(post, reason, old_slug=None):
    club_slug = getattr(getattr(post, "club", None), "slug", "")
    return schedule_revalidation(
        get_post_revalidation_paths(post, old_slug=old_slug),
        reason=reason,
        club_slug=club_slug,
    )


def get_post_category_revalidation_paths(category):
    paths = ["/", "/clanky", "/sitemap.xml"]
    paths.extend(get_club_post_category_paths(getattr(category, "club", None)))

    if category and getattr(category, "pk", None):
        post_slugs = category.posts.exclude(slug="").values_list("slug", flat=True)
        paths.extend(f"/clanky/{slug}" for slug in post_slugs)

    return paths


def revalidate_post_category_paths(category, reason):
    club_slug = getattr(getattr(category, "club", None), "slug", "")
    return schedule_revalidation(
        get_post_category_revalidation_paths(category),
        reason=reason,
        club_slug=club_slug,
    )

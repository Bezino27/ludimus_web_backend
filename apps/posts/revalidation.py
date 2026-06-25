from apps.common.revalidation import revalidate_paths


def get_post_revalidation_paths(post, old_slug=None):
    paths = ["/", "/clanky", "/sitemap.xml"]

    if getattr(post, "slug", ""):
        paths.append(f"/clanky/{post.slug}")

    if old_slug and old_slug != getattr(post, "slug", ""):
        paths.append(f"/clanky/{old_slug}")

    return paths


def revalidate_post_paths(post, reason, old_slug=None):
    club_slug = getattr(getattr(post, "club", None), "slug", "")
    revalidate_paths(
        get_post_revalidation_paths(post, old_slug=old_slug),
        reason=reason,
        club_slug=club_slug,
    )

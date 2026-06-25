from apps.common.revalidation import revalidate_paths


def revalidate_partner_paths(partner, reason):
    club_slug = getattr(getattr(partner, "club", None), "slug", "")
    revalidate_paths(["/"], reason=reason, club_slug=club_slug)

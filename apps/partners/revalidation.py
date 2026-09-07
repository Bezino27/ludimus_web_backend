from apps.common.revalidation import schedule_revalidation


def revalidate_partner_paths(partner, reason):
    club_slug = getattr(getattr(partner, "club", None), "slug", "")
    schedule_revalidation(["/"], reason=reason, club_slug=club_slug)

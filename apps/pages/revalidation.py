import logging

from apps.common.revalidation import revalidate_paths

logger = logging.getLogger(__name__)


def get_page_revalidation_path(page) -> str | None:
    if not page:
        return None

    if hasattr(page, "get_public_path"):
        return page.get_public_path()

    logger.info(
        "Skipping page revalidation for page without public path helper. page_id=%s slug=%s page_type=%s",
        getattr(page, "id", None),
        getattr(page, "slug", ""),
        getattr(page, "page_type", ""),
    )
    return None


def revalidate_page(page, reason: str = "") -> bool:
    path = get_page_revalidation_path(page)

    if not path:
        return False

    club_slug = getattr(getattr(page, "club", None), "slug", "")
    return revalidate_paths([path], reason=reason, club_slug=club_slug)


def revalidate_page_section(section, reason: str = "") -> bool:
    return revalidate_page(getattr(section, "page", None), reason=reason)

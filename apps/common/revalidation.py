import logging
import os
from typing import Iterable

import requests

logger = logging.getLogger(__name__)

MAX_PATHS = 20
MAX_PATH_LENGTH = 300
REQUEST_TIMEOUT_SECONDS = 4


def is_valid_revalidation_path(path: object) -> bool:
    return (
        isinstance(path, str)
        and path.startswith("/")
        and not path.startswith("//")
        and "://" not in path
        and len(path) <= MAX_PATH_LENGTH
    )


def normalize_revalidation_paths(paths: Iterable[object]) -> list[str]:
    normalized_paths: list[str] = []
    seen: set[str] = set()

    for path in paths:
        if not is_valid_revalidation_path(path):
            continue

        if path in seen:
            continue

        seen.add(path)
        normalized_paths.append(path)

        if len(normalized_paths) >= MAX_PATHS:
            break

    return normalized_paths


def revalidate_paths(
    paths: list[str],
    reason: str = "",
    club_slug: str = "",
) -> bool:
    revalidate_url = os.getenv("NEXT_REVALIDATE_URL", "").strip()
    revalidate_secret = os.getenv("NEXT_REVALIDATE_SECRET", "").strip()
    valid_paths = normalize_revalidation_paths(paths)

    if not valid_paths:
        logger.info("Next revalidation skipped: no valid paths. reason=%s", reason)
        return False

    if not revalidate_url or not revalidate_secret:
        logger.info(
            "Next revalidation skipped: NEXT_REVALIDATE_URL or NEXT_REVALIDATE_SECRET is missing. paths=%s reason=%s",
            valid_paths,
            reason,
        )
        return False

    try:
        response = requests.post(
            revalidate_url,
            json={
                "paths": valid_paths,
                "reason": reason,
                "club": club_slug,
            },
            headers={
                "Authorization": f"Bearer {revalidate_secret}",
                "Content-Type": "application/json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(
            "Next revalidation failed. paths=%s reason=%s error=%s",
            valid_paths,
            reason,
            exc,
            exc_info=True,
        )
        return False

    logger.info(
        "Next revalidation requested. paths=%s reason=%s club=%s",
        valid_paths,
        reason,
        club_slug,
    )
    return True

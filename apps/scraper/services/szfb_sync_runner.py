import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.scraper.models import SzfbCompetition
from apps.common.revalidation import schedule_revalidation
from apps.scraper.revalidation import get_competition_revalidation_paths
from apps.scraper.services.szfb_sync import sync_competition_from_home_url


logger = logging.getLogger(__name__)
STALE_RUNNING_SYNC_DELTA = timedelta(minutes=5)
BYPASS_RATE_LIMIT_USERNAME = "guli"
BYPASS_RATE_LIMIT_EMAIL = "guli@ludimus.sk"


def get_szfb_sync_rate_limit_delta():
    minutes = getattr(settings, "SZFB_SYNC_RATE_LIMIT_MINUTES", 1440)
    return timedelta(minutes=minutes)


def get_next_allowed_sync_at(competition: SzfbCompetition):
    if not competition.last_synced_at:
        return None

    return competition.last_synced_at + get_szfb_sync_rate_limit_delta()


def can_bypass_sync_rate_limit(user):
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and user.username == BYPASS_RATE_LIMIT_USERNAME
        and user.email == BYPASS_RATE_LIMIT_EMAIL
    )


def get_stale_running_sync_cutoff():
    return timezone.now() - STALE_RUNNING_SYNC_DELTA


def expire_stale_running_competition_syncs():
    cutoff = get_stale_running_sync_cutoff()
    now = timezone.now()
    error_text = (
        "Synchronizácia sa zasekla a bola automaticky ukončená "
        "po viac ako 5 minútach."
    )

    expired_count = SzfbCompetition.objects.filter(
        sync_status=SzfbCompetition.SYNC_STATUS_RUNNING,
    ).filter(
        sync_started_at__lt=cutoff,
    ).update(
        sync_status=SzfbCompetition.SYNC_STATUS_ERROR,
        sync_finished_at=now,
        sync_error=error_text,
    )

    missing_started_count = SzfbCompetition.objects.filter(
        sync_status=SzfbCompetition.SYNC_STATUS_RUNNING,
        sync_started_at__isnull=True,
    ).update(
        sync_status=SzfbCompetition.SYNC_STATUS_ERROR,
        sync_finished_at=now,
        sync_error=error_text,
    )

    total_count = expired_count + missing_started_count

    if total_count:
        logger.warning(
            "Expired %s stale SZFB running sync(s). cutoff=%s",
            total_count,
            cutoff,
        )
        print(f"SZFB sync expired stale running count={total_count} cutoff={cutoff}")

    return total_count


def can_start_competition_sync(competition: SzfbCompetition, user=None):
    is_stale_running_sync = False

    if competition.sync_status == SzfbCompetition.SYNC_STATUS_RUNNING:
        started_at = competition.sync_started_at

        if started_at and timezone.now() - started_at <= STALE_RUNNING_SYNC_DELTA:
            return False, "already_running", None

        is_stale_running_sync = True

        logger.warning(
            "Allowing SZFB sync restart for stale running competition %s. "
            "sync_started_at=%s",
            competition.id,
            started_at,
        )
        print(
            "SZFB sync restart allowed for stale running "
            f"competition_id={competition.id} sync_started_at={started_at}"
        )

    if not competition.source_url:
        return False, "missing_source_url", None

    next_allowed_at = get_next_allowed_sync_at(competition)

    if (
        not is_stale_running_sync
        and not can_bypass_sync_rate_limit(user)
        and next_allowed_at
        and timezone.now() < next_allowed_at
    ):
        return False, "rate_limited", next_allowed_at

    return True, "", None


def run_competition_sync(competition_id: int):
    try:
        print(f"SZFB sync started competition_id={competition_id}")
        logger.info("SZFB sync started competition_id=%s", competition_id)

        competition = SzfbCompetition.objects.get(id=competition_id)

        if not competition.source_url:
            raise ValueError("Súťaž nemá vyplnenú source_url.")

        synced_competition = sync_competition_from_home_url(
            competition.source_url,
            competition_id=competition.id,
        )

        synced_competition.sync_status = SzfbCompetition.SYNC_STATUS_SUCCESS
        synced_competition.sync_finished_at = timezone.now()
        synced_competition.sync_error = ""
        synced_competition.save(
            update_fields=[
                "sync_status",
                "sync_finished_at",
                "sync_error",
            ]
        )
        club_slug = (
            synced_competition.watched_teams
            .filter(is_active=True, club__isnull=False)
            .values_list("club__slug", flat=True)
            .first()
            or ""
        )
        schedule_revalidation(
            get_competition_revalidation_paths(synced_competition),
            reason="SZFB competition sync completed",
            club_slug=club_slug,
        )

        print(f"SZFB sync success competition_id={competition_id}")
        logger.info("SZFB sync success competition_id=%s", competition_id)

    except Exception as exc:
        error_text = str(exc)[:5000]

        SzfbCompetition.objects.filter(id=competition_id).update(
            sync_status=SzfbCompetition.SYNC_STATUS_ERROR,
            sync_finished_at=timezone.now(),
            sync_error=error_text,
        )

        print(f"SZFB sync error competition_id={competition_id}: {error_text}")
        logger.exception(
            "SZFB sync error competition_id=%s: %s",
            competition_id,
            error_text,
        )

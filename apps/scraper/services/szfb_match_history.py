import re
import unicodedata

from apps.scraper.models import SzfbMatchHistory


MATCH_HISTORY_LIMIT = 5


def normalize_team_identity(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def get_watch_team_identity(watch):
    return normalize_team_identity(watch.label or watch.team_name)


def is_valid_finished_result(result):
    return bool(re.fullmatch(r"\d+\s*:\s*\d+", (result or "").strip()))


def get_match_history_for_watch(watch):
    if not watch.club_id:
        return SzfbMatchHistory.objects.none()

    return SzfbMatchHistory.objects.filter(
        club_id=watch.club_id,
        team_identity=get_watch_team_identity(watch),
    ).order_by("-match_date", "-match_time", "-id")


def persist_finished_match_history(watch, matches):
    if not watch.club_id:
        return

    team_identity = get_watch_team_identity(watch)
    if not team_identity:
        return

    competition = watch.competition
    for match in matches:
        if (
            match.get("match_type") != "finished"
            or not match.get("match_date")
            or not is_valid_finished_result(match.get("result"))
        ):
            continue

        SzfbMatchHistory.objects.update_or_create(
            club_id=watch.club_id,
            team_identity=team_identity,
            external_key=match["external_key"],
            defaults={
                "team_label": watch.label,
                "team_name": watch.team_name,
                "competitor_id": watch.competitor_id,
                "szfb_competition_id": competition.szfb_competition_id,
                "competition_name": competition.name,
                "competition_season": competition.season,
                "match_date": match["match_date"],
                "match_time": match.get("match_time"),
                "opponent": match["opponent"],
                "venue": match.get("venue", ""),
                "result": match["result"].strip(),
                "is_home": match.get("is_home"),
            },
        )

    retained_ids = list(
        get_match_history_for_watch(watch).values_list("id", flat=True)[:MATCH_HISTORY_LIMIT]
    )
    get_match_history_for_watch(watch).exclude(id__in=retained_ids).delete()

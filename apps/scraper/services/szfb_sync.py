from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.scraper.models import (
    ClubPlayer,
    SzfbCompetition,
    SzfbGoalieStat,
    SzfbMatch,
    SzfbPlayerStat,
    SzfbStandingRow,
    SzfbTeamWatch,
    build_club_player_identity_key,
    normalize_player_name,
)
from apps.scraper.services.szfb_match_history import persist_finished_match_history
from apps.scraper.services.szfb_scraper import (
    build_team_player_stats_url,
    extract_competition_info,
    fetch_matches,
    fetch_standings,
    fetch_team_player_stats,
    filter_matches_for_team,
)


def _get_or_create_club_player(watch: SzfbTeamWatch, player_data: dict):
    club = watch.club
    if not club:
        return None

    szfb_player_id = player_data.get("szfb_player_id")
    if szfb_player_id:
        linked_player = (
            ClubPlayer.objects.filter(club=club)
            .filter(
                Q(szfb_stats__szfb_player_id=szfb_player_id)
                | Q(szfb_goalie_stats__szfb_player_id=szfb_player_id)
            )
            .distinct()
            .first()
        )
        if linked_player:
            return linked_player

    player_name = player_data["player_name"]
    birth_year = player_data.get("birth_year")
    normalized_name = normalize_player_name(player_name)
    identity_key = build_club_player_identity_key(player_name, birth_year)
    player_position = player_data.get("player_position") or ""
    jersey_number = player_data.get("jersey_number")

    club_player, created = ClubPlayer.objects.get_or_create(
        club=club,
        identity_key=identity_key,
        defaults={
            "full_name": player_name,
            "normalized_name": normalized_name,
            "birth_year": birth_year,
            "position": player_position,
            "jersey_number": jersey_number,
        },
    )

    changed_fields = []
    if not created:
        if not club_player.normalized_name:
            club_player.normalized_name = normalized_name
            changed_fields.append("normalized_name")
        if not club_player.birth_year and birth_year:
            club_player.birth_year = birth_year
            changed_fields.append("birth_year")
        if not club_player.position and player_position:
            club_player.position = player_position
            changed_fields.append("position")
        if club_player.jersey_number is None and jersey_number is not None:
            club_player.jersey_number = jersey_number
            changed_fields.append("jersey_number")
        if changed_fields:
            club_player.save(update_fields=changed_fields)

    return club_player


def _get_legacy_player_fields_from_club_player(club_player: ClubPlayer | None):
    if not club_player:
        return {
            "photo": "",
            "jersey_number": None,
            "bio": "",
            "is_active": True,
            "is_featured": False,
            "display_order": 0,
        }

    return {
        "photo": club_player.photo.name if club_player.photo else "",
        "jersey_number": club_player.jersey_number,
        "bio": club_player.bio,
        "is_active": club_player.is_active,
        "is_featured": club_player.is_featured,
        "display_order": club_player.display_order,
    }


def _find_legacy_player_stat(watch: SzfbTeamWatch, player_data: dict):
    candidates = SzfbPlayerStat.objects.filter(
        watched_team=watch,
        szfb_player_id__isnull=True,
        birth_year=player_data.get("birth_year"),
    )
    normalized_name = normalize_player_name(player_data["player_name"])
    return next(
        (
            candidate
            for candidate in candidates
            if normalize_player_name(candidate.player_name) == normalized_name
        ),
        None,
    )


def _upsert_player_stats(watch: SzfbTeamWatch, player_stats: list[dict]):
    valid_ids = []
    stat_fields = [
        "rank", "player_name", "birth_year", "team_short_name",
        "player_position", "games", "goals", "assists", "points",
        "points_avg", "esp", "ppp", "shp", "pim",
    ]

    for item in player_stats:
        szfb_player_id = item["szfb_player_id"]
        valid_ids.append(szfb_player_id)
        stat = SzfbPlayerStat.objects.filter(
            watched_team=watch,
            szfb_player_id=szfb_player_id,
        ).first()
        if not stat:
            stat = _find_legacy_player_stat(watch, item)

        if stat:
            update_fields = ["szfb_player_id", *stat_fields]
            stat.szfb_player_id = szfb_player_id
            for field_name in stat_fields:
                setattr(stat, field_name, item[field_name])

            if not stat.club_player_id:
                stat.club_player = _get_or_create_club_player(watch, item)
                update_fields.append("club_player")

            stat.save(update_fields=update_fields)
            continue

        club_player = _get_or_create_club_player(watch, item)
        legacy_fields = _get_legacy_player_fields_from_club_player(club_player)
        SzfbPlayerStat.objects.create(
            watched_team=watch,
            club_player=club_player,
            szfb_player_id=szfb_player_id,
            **{field_name: item[field_name] for field_name in stat_fields},
            **legacy_fields,
        )

    SzfbPlayerStat.objects.filter(watched_team=watch).exclude(
        szfb_player_id__in=valid_ids
    ).delete()


def _upsert_goalie_stats(watch: SzfbTeamWatch, goalie_stats: list[dict]):
    valid_ids = []
    stat_fields = [
        "rank", "jersey_number", "player_name", "birth_year", "games",
        "wins", "overtime_wins", "losses", "overtime_losses",
        "shots_against", "goals_against", "goals_against_average", "saves",
        "save_percentage", "minutes_played_seconds", "shutouts",
    ]

    for item in goalie_stats:
        szfb_player_id = item["szfb_player_id"]
        valid_ids.append(szfb_player_id)
        stat = SzfbGoalieStat.objects.filter(
            watched_team=watch,
            szfb_player_id=szfb_player_id,
        ).first()

        if stat:
            update_fields = [*stat_fields]
            for field_name in stat_fields:
                setattr(stat, field_name, item[field_name])

            if not stat.club_player_id:
                stat.club_player = _get_or_create_club_player(watch, item)
                update_fields.append("club_player")

            stat.save(update_fields=update_fields)
            continue

        club_player = _get_or_create_club_player(watch, item)
        SzfbGoalieStat.objects.create(
            watched_team=watch,
            club_player=club_player,
            szfb_player_id=szfb_player_id,
            **{field_name: item[field_name] for field_name in stat_fields},
        )

    SzfbGoalieStat.objects.filter(watched_team=watch).exclude(
        szfb_player_id__in=valid_ids
    ).delete()


def _resolve_existing_competition(data: dict, competition_id: int | None):
    if competition_id:
        return SzfbCompetition.objects.get(id=competition_id)
    return (
        SzfbCompetition.objects.filter(source_url=data["source_url"]).first()
        or SzfbCompetition.objects.filter(
            szfb_competition_id=data["szfb_competition_id"]
        ).first()
    )


def sync_competition_from_home_url(
    home_url: str,
    competition_id: int | None = None,
    watch_ids: list[int] | None = None,
):
    # All remote documents are fetched and validated before DB replacement starts.
    data = extract_competition_info(home_url)
    existing_competition = _resolve_existing_competition(data, competition_id)
    watch_queryset = SzfbTeamWatch.objects.select_related(
        "club", "competition"
    ).filter(competition=existing_competition, is_active=True)
    if watch_ids is not None:
        watch_queryset = watch_queryset.filter(id__in=watch_ids)
    watches = list(watch_queryset) if existing_competition else []
    standings = (
        fetch_standings(data["standings_url"])
        if data["standings_url"]
        else None
    )
    all_matches = (
        fetch_matches(data["results_url"])
        if data["results_url"]
        else None
    )
    watch_payloads = {}

    for watch in watches:
        payload = {
            "matches": (
                filter_matches_for_team(all_matches, watch.team_name)
                if all_matches is not None
                else None
            ),
            "player_stats": None,
        }
        if watch.competitor_id:
            player_stats_url = build_team_player_stats_url(
                competition_id=data["szfb_competition_id"],
                competition_name=data["name"],
                competitor_id=watch.competitor_id,
                team_name=watch.team_name,
            )
            payload["player_stats"] = fetch_team_player_stats(player_stats_url)
        watch_payloads[watch.id] = payload

    with transaction.atomic():
        if existing_competition:
            competition = SzfbCompetition.objects.select_for_update().get(
                id=existing_competition.id
            )
            for field_name in [
                "szfb_competition_id", "name", "season", "source_url",
                "standings_url", "results_url",
            ]:
                setattr(competition, field_name, data[field_name])
            competition.save(
                update_fields=[
                    "szfb_competition_id", "name", "season", "source_url",
                    "standings_url", "results_url",
                ]
            )
        else:
            competition, _ = SzfbCompetition.objects.update_or_create(
                szfb_competition_id=data["szfb_competition_id"],
                defaults={
                    "name": data["name"],
                    "season": data["season"],
                    "source_url": data["source_url"],
                    "standings_url": data["standings_url"],
                    "results_url": data["results_url"],
                },
            )

        if standings is not None:
            competition.standings.all().delete()
            SzfbStandingRow.objects.bulk_create(
                [
                    SzfbStandingRow(
                        competition=competition,
                        position=row["position"],
                        team_name=row["team_name"],
                        played=row["played"],
                        points=row["points"],
                    )
                    for row in standings
                ]
            )

        locked_watches = {
            watch.id: watch
            for watch in SzfbTeamWatch.objects.select_for_update()
            .filter(id__in=watch_payloads)
        }
        for watch_id, payload in watch_payloads.items():
            watch = locked_watches[watch_id]
            if payload["matches"] is not None:
                watch.matches.all().delete()
                SzfbMatch.objects.bulk_create(
                    [
                        SzfbMatch(
                            watched_team=watch,
                            match_type=item["match_type"],
                            match_date=item["match_date"],
                            match_time=item["match_time"],
                            opponent=item["opponent"],
                            venue=item["venue"],
                            result=item["result"],
                            is_home=item["is_home"],
                            external_key=item["external_key"],
                        )
                        for item in payload["matches"]
                    ],
                    ignore_conflicts=True,
                )
                persist_finished_match_history(watch, payload["matches"])

            if payload["player_stats"] is not None:
                _upsert_player_stats(watch, payload["player_stats"]["players"])
                _upsert_goalie_stats(watch, payload["player_stats"]["goalies"])

        competition.last_synced_at = timezone.now()
        competition.save(update_fields=["last_synced_at"])

    return competition

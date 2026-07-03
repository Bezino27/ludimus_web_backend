from django.utils import timezone

from apps.scraper.models import (
    ClubPlayer,
    SzfbCompetition,
    SzfbMatch,
    SzfbPlayerStat,
    SzfbStandingRow,
    SzfbTeamWatch,
    build_club_player_identity_key,
    normalize_player_name,
)

from apps.scraper.services.szfb_scraper import (
    build_players_productivity_url,
    extract_competition_info,
    fetch_matches,
    fetch_player_productivity,
    fetch_standings,
    filter_matches_for_team,
)


def _get_or_create_club_player(watch: SzfbTeamWatch, player_data: dict):
    club = watch.club

    if not club:
        return None

    player_name = player_data["player_name"]
    birth_year = player_data["birth_year"]
    normalized_name = normalize_player_name(player_name)
    identity_key = build_club_player_identity_key(player_name, birth_year)

    club_player, created = ClubPlayer.objects.get_or_create(
        club=club,
        identity_key=identity_key,
        defaults={
            "full_name": player_name,
            "normalized_name": normalized_name,
            "birth_year": birth_year,
            "position": player_data.get("player_position") or "",
        },
    )

    changed_fields = []

    if not created:
        if not club_player.full_name and player_name:
            club_player.full_name = player_name
            changed_fields.append("full_name")

        if not club_player.normalized_name:
            club_player.normalized_name = normalized_name
            changed_fields.append("normalized_name")

        if not club_player.birth_year and birth_year:
            club_player.birth_year = birth_year
            changed_fields.append("birth_year")

        if not club_player.position and player_data.get("player_position"):
            club_player.position = player_data["player_position"]
            changed_fields.append("position")

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


def sync_competition_from_home_url(home_url: str, competition_id: int | None = None):
    data = extract_competition_info(home_url)

    if competition_id:
        competition = SzfbCompetition.objects.get(id=competition_id)

        competition.szfb_competition_id = data["szfb_competition_id"]
        competition.name = data["name"]
        competition.season = data["season"]
        competition.source_url = data["source_url"]
        competition.standings_url = data["standings_url"]
        competition.results_url = data["results_url"]
        competition.last_synced_at = timezone.now()
        competition.save(
            update_fields=[
                "szfb_competition_id",
                "name",
                "season",
                "source_url",
                "standings_url",
                "results_url",
                "last_synced_at",
            ]
        )
    else:
        existing_competition = (
            SzfbCompetition.objects
            .filter(source_url=home_url)
            .first()
        )

        if existing_competition:
            competition = existing_competition
            competition.szfb_competition_id = data["szfb_competition_id"]
            competition.name = data["name"]
            competition.season = data["season"]
            competition.source_url = data["source_url"]
            competition.standings_url = data["standings_url"]
            competition.results_url = data["results_url"]
            competition.last_synced_at = timezone.now()
            competition.save(
                update_fields=[
                    "szfb_competition_id",
                    "name",
                    "season",
                    "source_url",
                    "standings_url",
                    "results_url",
                    "last_synced_at",
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
                    "last_synced_at": timezone.now(),
                },
            )

    if competition.standings_url:
        standings = fetch_standings(competition.standings_url)

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

    watches = (
        SzfbTeamWatch.objects
        .select_related("club", "competition")
        .filter(
            competition=competition,
            is_active=True,
        )
    )

    if competition.results_url:
        all_matches = fetch_matches(competition.results_url)

        for watch in watches:
            watch.matches.all().delete()

            filtered_matches = filter_matches_for_team(
                matches=all_matches,
                team_name=watch.team_name,
            )

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
                    for item in filtered_matches
                ],
                ignore_conflicts=True,
            )

    for watch in watches:
        if not watch.competitor_id:
            continue

        players_url = build_players_productivity_url(
            competition_id=competition.szfb_competition_id,
            competition_name=competition.name,
            competitor_id=watch.competitor_id,
        )

        player_stats = fetch_player_productivity(players_url)

        watch.player_stats.all().delete()

        players_to_create = []

        for item in player_stats:
            club_player = _get_or_create_club_player(watch, item)
            legacy_fields = _get_legacy_player_fields_from_club_player(club_player)

            players_to_create.append(
                SzfbPlayerStat(
                    watched_team=watch,
                    club_player=club_player,
                    rank=item["rank"],
                    player_name=item["player_name"],
                    birth_year=item["birth_year"],
                    team_short_name=item["team_short_name"],
                    player_position=item["player_position"],
                    games=item["games"],
                    goals=item["goals"],
                    assists=item["assists"],
                    points=item["points"],
                    points_avg=item["points_avg"],
                    esp=item["esp"],
                    ppp=item["ppp"],
                    shp=item["shp"],
                    pim=item["pim"],
                    photo=legacy_fields["photo"],
                    jersey_number=legacy_fields["jersey_number"],
                    bio=legacy_fields["bio"],
                    is_active=legacy_fields["is_active"],
                    is_featured=legacy_fields["is_featured"],
                    display_order=legacy_fields["display_order"],
                )
            )

        SzfbPlayerStat.objects.bulk_create(players_to_create)

    competition.last_synced_at = timezone.now()
    competition.save(update_fields=["last_synced_at"])

    return competition
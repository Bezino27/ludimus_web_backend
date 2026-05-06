from django.utils import timezone

from apps.scraper.models import (
    SzfbCompetition,
    SzfbMatch,
    SzfbPlayerStat,
    SzfbStandingRow,
    SzfbTeamWatch,
)

from apps.scraper.services.szfb_scraper import (
    build_players_productivity_url,
    extract_competition_info,
    fetch_matches,
    fetch_player_productivity,
    fetch_standings,
    filter_matches_for_team,
)


def sync_competition_from_home_url(home_url: str):
    """
    Hlavná sync funkcia.

    Spraví:
    1. načíta základné info o súťaži,
    2. uloží / aktualizuje SzfbCompetition,
    3. stiahne tabuľku súťaže,
    4. stiahne zápasy sledovaných tímov,
    5. stiahne produktivitu hráčov sledovaných tímov.
    """

    # # 1. ZÁKLADNÉ INFO O SÚŤAŽI

    data = extract_competition_info(home_url)

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

    # # 2. TABUĽKA SÚŤAŽE

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

    # # 3. AKTÍVNE SLEDOVANÉ TÍMY

    watches = SzfbTeamWatch.objects.filter(
        competition=competition,
        is_active=True,
    )

    # # 4. ZÁPASY SLEDOVANÝCH TÍMOV

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
                ]
            )

    # # 5. PRODUKTIVITA HRÁČOV SLEDOVANÝCH TÍMOV

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

        SzfbPlayerStat.objects.bulk_create(
            [
                SzfbPlayerStat(
                    watched_team=watch,
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
                )
                for item in player_stats
            ]
        )

    # # 6. OZNAČENIE ČASU POSLEDNÉHO SYNCU

    competition.last_synced_at = timezone.now()
    competition.save(update_fields=["last_synced_at"])

    return competition
from django.utils import timezone

from apps.scraper.models import (
    SzfbCompetition,
    SzfbMatch,
    SzfbStandingRow,
    SzfbTeamWatch,
)
from apps.scraper.services.szfb_scraper import (
    extract_competition_info,
    fetch_matches,
    fetch_standings,
    filter_matches_for_team,
)


def sync_competition_from_home_url(home_url: str):
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

    if competition.results_url:
        all_matches = fetch_matches(competition.results_url)

        watches = SzfbTeamWatch.objects.filter(
            competition=competition,
            is_active=True,
        )

        for watch in watches:
            watch.matches.all().delete()

            filtered_matches = filter_matches_for_team(all_matches, watch.team_name)

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

    competition.last_synced_at = timezone.now()
    competition.save(update_fields=["last_synced_at"])

    return competition
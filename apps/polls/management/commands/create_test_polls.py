from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.polls.models import Poll, PollOption, PollVote


class Command(BaseCommand):
    help = "Create realistic test polls for frontend development."

    def handle(self, *args, **options):
        now = timezone.now()

        with transaction.atomic():
            Poll.objects.filter(question__startswith="[TEST]").delete()

            active_poll = self.create_poll(
                question="[TEST] Kto bol hráč zápasu?",
                description="Vyber hráča, ktorý podľa teba podal najlepší výkon.",
                is_active=True,
                starts_at=now - timedelta(hours=1),
                ends_at=now + timedelta(days=2),
                options=[
                    "Adam Novák",
                    "Samuel Horváth",
                    "Matúš Kováč",
                    "Tomáš Urban",
                ],
            )

            ended_poll = self.create_poll(
                question="[TEST] Najkrajší gól mesiaca",
                description="Výsledok poslednej ukončenej ankety.",
                is_active=True,
                starts_at=now - timedelta(days=10),
                ends_at=now - timedelta(days=2),
                options=[
                    "Gól proti Žiline",
                    "Gól proti Prešovu",
                    "Gól proti Trenčínu",
                ],
            )

            self.create_votes(
                poll=ended_poll,
                votes_by_option={
                    "Gól proti Žiline": 8,
                    "Gól proti Prešovu": 4,
                    "Gól proti Trenčínu": 2,
                },
            )

            future_poll = self.create_poll(
                question="[TEST] Budúca anketa",
                description="Táto anketa sa ešte nemá zobrazovať na webe.",
                is_active=True,
                starts_at=now + timedelta(days=7),
                ends_at=now + timedelta(days=10),
                options=[
                    "Áno",
                    "Nie",
                ],
            )

            created_polls = [active_poll, ended_poll, future_poll]
            created_options_count = PollOption.objects.filter(
                poll__in=created_polls,
            ).count()
            created_votes_count = PollVote.objects.filter(
                poll__in=created_polls,
            ).count()

        self.stdout.write(
            self.style.SUCCESS(
                "Created test poll data: "
                f"{len(created_polls)} polls, "
                f"{created_options_count} options, "
                f"{created_votes_count} votes."
            )
        )

    def create_poll(
        self,
        *,
        question,
        description,
        is_active,
        starts_at,
        ends_at,
        options,
    ):
        poll = Poll.objects.create(
            question=question,
            description=description,
            is_active=is_active,
            starts_at=starts_at,
            ends_at=ends_at,
        )

        for index, option_text in enumerate(options, start=1):
            PollOption.objects.create(
                poll=poll,
                text=option_text,
                order=index,
            )

        return poll

    def create_votes(self, *, poll, votes_by_option):
        voter_index = 1
        options_by_text = {
            option.text: option
            for option in poll.options.all()
        }

        for option_text, vote_count in votes_by_option.items():
            option = options_by_text[option_text]

            for _ in range(vote_count):
                PollVote.objects.create(
                    poll=poll,
                    option=option,
                    voter_id=f"test-voter-goal-{voter_index}",
                )
                voter_index += 1

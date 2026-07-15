from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Poll, PollOption, PollVote
from .serializers import PollCreateSerializer, PollSerializer, PollVoteSerializer
from .utils import (
    get_ip_hash,
    get_or_create_voter_id,
    get_user_agent_hash,
    set_voter_cookie,
)


MAX_VOTES_PER_IP_PER_POLL = 5


def filter_polls_by_club_param(queryset, request):
    club_slug = request.query_params.get("club")

    if not club_slug:
        return queryset

    return queryset.filter(club__slug=club_slug)


def get_video_file_url(option, request=None):
    if not option.video_file:
        return None

    video_url = option.video_file.url

    if request:
        return request.build_absolute_uri(video_url)

    return video_url


def build_poll_results_response_data(poll, request=None):
    options = poll.options.annotate(
        votes_count=Count("votes")
    ).order_by("order", "id")

    total_votes = PollVote.objects.filter(poll=poll).count()

    results = []

    for option in options:
        votes_count = option.votes_count

        if total_votes > 0:
            percent = round((votes_count / total_votes) * 100, 2)
        else:
            percent = 0

        results.append(
            {
                "id": option.id,
                "text": option.text,
                "video_url": option.video_url,
                "video_file": option.video_file.name if option.video_file else None,
                "video_file_url": get_video_file_url(option, request),
                "votes": votes_count,
                "percent": percent,
            }
        )

    return {
        "poll_id": poll.id,
        "question": poll.question,
        "description": poll.description,
        "voting_open": poll.is_open_for_voting,
        "starts_at": poll.starts_at,
        "ends_at": poll.ends_at,
        "total_votes": total_votes,
        "options": results,
    }


def serialize_polls_with_voter_state(polls, voter_id, request=None):
    serializer = PollSerializer(polls, many=True, context={"request": request})
    data = serializer.data

    voted_poll_ids = set()

    if voter_id:
        voted_poll_ids = set(
            PollVote.objects.filter(
                poll__in=polls,
                voter_id=voter_id,
            ).values_list("poll_id", flat=True)
        )

    for item in data:
        item["has_voted"] = item["id"] in voted_poll_ids

    return data


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def poll_list_create_view(request):
    """
    GET:
    - vráti iba ankety, ktoré sú práve otvorené na hlasovanie
    - zároveň vytvorí anonymnú voter_id cookie, ak ešte neexistuje

    POST:
    - vytvorí novú anketu
    - povolené iba pre admina / staff používateľa
    """

    if request.method == "GET":
        now = timezone.now()

        polls = list(
            filter_polls_by_club_param(
                Poll.objects.filter(
                    is_active=True,
                )
                .filter(
                    Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                    Q(ends_at__isnull=True) | Q(ends_at__gte=now),
                ),
                request,
            )
            .prefetch_related("options")
            .order_by("-created_at")[:2]
        )

        voter_id, voter_id_created = get_or_create_voter_id(request)

        response = Response(
            serialize_polls_with_voter_state(polls, voter_id, request),
            status=status.HTTP_200_OK,
        )

        if voter_id_created:
            set_voter_cookie(response, voter_id)

        return response

    if request.method == "POST":
        if not request.user.is_authenticated or not request.user.is_staff:
            return Response(
                {"detail": "Nemáš oprávnenie vytvoriť anketu."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PollCreateSerializer(data=request.data)

        if serializer.is_valid():
            try:
                poll = serializer.save()
            except DjangoValidationError as error:
                return Response(
                    {"detail": error.messages},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            response_serializer = PollSerializer(poll, context={"request": request})

            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([AllowAny])
def poll_detail_view(request, poll_id):
    """
    Vráti detail jednej ankety + informáciu, či tento prehliadač už hlasoval.
    """

    poll = get_object_or_404(Poll, id=poll_id)

    voter_id, voter_id_created = get_or_create_voter_id(request)

    has_voted = PollVote.objects.filter(
        poll=poll,
        voter_id=voter_id,
    ).exists()

    serializer = PollSerializer(poll, context={"request": request})

    data = serializer.data
    data["has_voted"] = has_voted

    response = Response(data, status=status.HTTP_200_OK)

    if voter_id_created:
        set_voter_cookie(response, voter_id)

    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def poll_vote_view(request, poll_id):
    """
    Uloží hlas v ankete.

    Duálna ochrana:
    1. voter_id cookie = rovnaký prehliadač môže hlasovať iba raz
    2. ip_hash limit = max. 6 hlasov z jednej IP adresy pre jednu anketu
    """

    poll = get_object_or_404(Poll, id=poll_id)

    if not poll.is_open_for_voting:
        return Response(
            {"detail": "V tejto ankete sa momentálne nedá hlasovať."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    voter_id, voter_id_created = get_or_create_voter_id(request)
    ip_hash = get_ip_hash(request)
    user_agent_hash = get_user_agent_hash(request)

    serializer = PollVoteSerializer(
        data=request.data,
        context={"poll": poll},
    )

    if not serializer.is_valid():
        response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if voter_id_created:
            set_voter_cookie(response, voter_id)

        return response

    option_id = serializer.validated_data["option_id"]
    option = get_object_or_404(PollOption, id=option_id, poll=poll)

    already_voted_by_cookie = PollVote.objects.filter(
        poll=poll,
        voter_id=voter_id,
    ).exists()

    if already_voted_by_cookie:
        response = Response(
            {"detail": "V tejto ankete si už hlasoval."},
            status=status.HTTP_409_CONFLICT,
        )

        if voter_id_created:
            set_voter_cookie(response, voter_id)

        return response

    ip_votes_count = PollVote.objects.filter(
        poll=poll,
        ip_hash=ip_hash,
    ).count()

    if ip_votes_count >= MAX_VOTES_PER_IP_PER_POLL:
        response = Response(
            {
                "detail": (
                    "Z tejto siete už bolo odoslaných maximum hlasov "
                    "pre túto anketu."
                )
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

        if voter_id_created:
            set_voter_cookie(response, voter_id)

        return response

    try:
        PollVote.objects.create(
            poll=poll,
            option=option,
            voter_id=voter_id,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
        )
    except IntegrityError:
        response = Response(
            {"detail": "V tejto ankete si už hlasoval."},
            status=status.HTTP_409_CONFLICT,
        )

        if voter_id_created:
            set_voter_cookie(response, voter_id)

        return response
    except DjangoValidationError as error:
        response = Response(
            {"detail": error.messages},
            status=status.HTTP_400_BAD_REQUEST,
        )

        if voter_id_created:
            set_voter_cookie(response, voter_id)

        return response

    response = Response(
        {
            "message": "Hlas bol uložený.",
            "has_voted": True,
        },
        status=status.HTTP_201_CREATED,
    )

    if voter_id_created:
        set_voter_cookie(response, voter_id)

    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def poll_results_view(request, poll_id):
    """
    Vráti výsledky konkrétnej ankety.
    """

    poll = get_object_or_404(Poll, id=poll_id)

    return Response(
        build_poll_results_response_data(poll, request),
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def latest_poll_result_view(request):
    """
    Vráti poslednú ukončenú anketu.

    Za ukončenú berieme anketu, ktorá už začala a buď:
    - je ručne vypnutá cez is_active=False,
    - alebo jej ends_at je už v minulosti.

    Budúce pripravené ankety sa tu nezobrazujú.
    Aktuálne otvorené ankety sa tu tiež nezobrazujú.
    """

    now = timezone.now()

    already_started = Q(starts_at__isnull=True) | Q(starts_at__lte=now)
    manually_closed = Q(is_active=False)
    ended_by_date = Q(ends_at__isnull=False, ends_at__lt=now)

    poll = (
        filter_polls_by_club_param(
            Poll.objects.filter(already_started),
            request,
        )
        .filter(manually_closed | ended_by_date)
        .order_by("-ends_at", "-updated_at", "-created_at")
        .first()
    )

    if not poll:
        return Response(None, status=status.HTTP_200_OK)

    return Response(
        build_poll_results_response_data(poll, request),
        status=status.HTTP_200_OK,
    )

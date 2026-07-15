import re

from django.db.models import Count, Prefetch, Q
from django.http import QueryDict
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.clubs.models import ClubMembership
from apps.common.permissions import EDITOR_ROLES, user_has_club_role

from .admin_serializers import PollAdminSerializer
from .models import Poll, PollOption


class AdminPollViewSet(viewsets.ModelViewSet):
    serializer_class = PollAdminSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    option_field_pattern = re.compile(r"^options\[(?P<index>\d+)\]\[(?P<field>[a-zA-Z0-9_]+)\]$")

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs and self._is_multipart_request():
            kwargs["data"] = self._normalize_multipart_poll_data(kwargs["data"])

        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        options_queryset = PollOption.objects.annotate(
            votes_count=Count("votes")
        ).order_by("order", "id")

        queryset = (
            Poll.objects.select_related("club")
            .prefetch_related(Prefetch("options", queryset=options_queryset))
            .annotate(total_votes=Count("votes"))
            .order_by("-created_at")
        )

        if not (user.is_staff or user.is_superuser):
            club_ids = ClubMembership.objects.filter(
                user=user,
                is_active=True,
                role__in=EDITOR_ROLES,
            ).values_list("club_id", flat=True)
            queryset = queryset.filter(club_id__in=club_ids)

        club_value = self.request.query_params.get("club")

        if club_value:
            club_filter = Q(club__slug=club_value)

            if club_value.isdigit():
                club_filter |= Q(club_id=int(club_value))

            queryset = queryset.filter(club_filter)

        return queryset

    def perform_create(self, serializer):
        club = serializer.validated_data["club"]

        if not self._can_manage_club(club):
            raise PermissionDenied("Nemáš oprávnenie vytvárať ankety pre tento klub.")

        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()

        if not self._can_manage_club(instance.club):
            raise PermissionDenied("Nemáš oprávnenie upravovať túto anketu.")

        new_club = serializer.validated_data.get("club")

        if new_club and not self._can_manage_club(new_club):
            raise PermissionDenied("Nemáš oprávnenie presunúť anketu do tohto klubu.")

        serializer.save()

    def perform_destroy(self, instance):
        if not self._can_manage_club(instance.club):
            raise PermissionDenied("Nemáš oprávnenie zmazať túto anketu.")

        instance.delete()

    def _can_manage_club(self, club):
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return True

        return user_has_club_role(user, club, EDITOR_ROLES)

    def _is_multipart_request(self):
        return self.request.content_type.startswith("multipart/form-data")

    def _normalize_multipart_poll_data(self, data):
        if isinstance(data, QueryDict):
            payload = {
                key: value
                for key, value in data.items()
                if not self.option_field_pattern.match(key)
            }
        else:
            payload = {
                key: value
                for key, value in dict(data).items()
                if not self.option_field_pattern.match(key)
            }

        options_by_index = {}

        for source in [self.request.data, self.request.FILES]:
            for key, value in source.items():
                match = self.option_field_pattern.match(key)

                if not match:
                    continue

                index = int(match.group("index"))
                field = match.group("field")
                options_by_index.setdefault(index, {})[field] = value

        options = []

        for index in sorted(options_by_index):
            option = options_by_index[index]

            if option.get("id") == "":
                option.pop("id", None)

            if "remove_video_file" in option:
                option["remove_video_file"] = str(option["remove_video_file"]).lower() in {
                    "1",
                    "true",
                    "yes",
                    "on",
                }

            options.append(option)

        payload["options"] = options

        return payload

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.common.permissions import EDITOR_ROLES, user_has_club_role

from .models import Poll, PollOption


def format_django_validation_error(error):
    return getattr(error, "message_dict", None) or error.messages


class PollOptionAdminSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    votes_count = serializers.SerializerMethodField()
    video_file_url = serializers.SerializerMethodField()
    remove_video_file = serializers.BooleanField(
        required=False,
        write_only=True,
        default=False,
    )

    class Meta:
        model = PollOption
        fields = [
            "id",
            "text",
            "video_url",
            "video_file",
            "video_file_url",
            "remove_video_file",
            "order",
            "votes_count",
        ]

    def get_votes_count(self, obj):
        if hasattr(obj, "votes_count"):
            return obj.votes_count

        return obj.votes.count()

    def get_video_file_url(self, obj):
        if not obj.video_file:
            return None

        request = self.context.get("request")
        video_url = obj.video_file.url

        if request:
            return request.build_absolute_uri(video_url)

        return video_url


class PollAdminSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    club_slug = serializers.CharField(source="club.slug", read_only=True)
    voting_open = serializers.BooleanField(source="is_open_for_voting", read_only=True)
    options = PollOptionAdminSerializer(many=True)
    total_votes = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = [
            "id",
            "club",
            "club_name",
            "club_slug",
            "question",
            "description",
            "is_active",
            "starts_at",
            "ends_at",
            "voting_open",
            "created_at",
            "updated_at",
            "options",
            "total_votes",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "voting_open",
            "total_votes",
        ]
        extra_kwargs = {
            "club": {"required": True, "allow_null": False},
            "question": {"allow_blank": False},
        }

    def get_total_votes(self, obj):
        if hasattr(obj, "total_votes"):
            return obj.total_votes

        return obj.votes.count()

    def validate_club(self, club):
        request = self.context["request"]
        user = request.user

        if user.is_staff or user.is_superuser:
            return club

        if not user_has_club_role(user, club, EDITOR_ROLES):
            raise serializers.ValidationError("Nemáš oprávnenie pre tento klub.")

        return club

    def validate_options(self, options):
        if len(options) < 2:
            raise serializers.ValidationError("Anketa musí mať aspoň 2 možnosti.")

        option_texts = [option["text"].strip().lower() for option in options]

        if len(option_texts) != len(set(option_texts)):
            raise serializers.ValidationError("Možnosti odpovedí sa nesmú opakovať.")

        return options

    def validate(self, attrs):
        if self.instance is None and "options" not in attrs:
            raise serializers.ValidationError(
                {"options": "Anketa musí mať aspoň 2 možnosti."}
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        options_data = validated_data.pop("options")

        try:
            poll = Poll.objects.create(**validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"detail": error.messages})

        try:
            self._sync_options(poll, options_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "options": format_django_validation_error(error),
            })

        return poll

    @transaction.atomic
    def update(self, instance, validated_data):
        options_data = validated_data.pop("options", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        try:
            instance.save()
        except DjangoValidationError as error:
            raise serializers.ValidationError({"detail": error.messages})

        if options_data is not None:
            try:
                self._sync_options(instance, options_data)
            except DjangoValidationError as error:
                raise serializers.ValidationError({
                    "options": format_django_validation_error(error),
                })

        return instance

    def _sync_options(self, poll, options_data):
        existing_options = {option.id: option for option in poll.options.all()}
        seen_option_ids = set()

        for index, option_data in enumerate(options_data):
            option_id = option_data.get("id")

            if option_id:
                option = existing_options.get(option_id)

                if not option:
                    raise serializers.ValidationError(
                        {"options": f"Možnosť s id {option_id} nepatrí k tejto ankete."}
                    )

                option.text = option_data["text"]
                option.video_url = option_data.get("video_url", "")
                if option_data.get("remove_video_file"):
                    option.video_file = None
                elif option_data.get("video_file") is not None:
                    option.video_file = option_data.get("video_file")
                option.order = option_data.get("order", index)
                option.save()
                seen_option_ids.add(option_id)
                continue

            option = PollOption.objects.create(
                poll=poll,
                text=option_data["text"],
                video_url=option_data.get("video_url", ""),
                video_file=option_data.get("video_file"),
                order=option_data.get("order", index),
            )
            seen_option_ids.add(option.id)

        poll.options.exclude(id__in=seen_option_ids).delete()

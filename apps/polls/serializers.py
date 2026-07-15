from rest_framework import serializers

from .models import Poll, PollOption, PollVote


class PollOptionSerializer(serializers.ModelSerializer):
    votes_count = serializers.IntegerField(read_only=True)
    video_file_url = serializers.SerializerMethodField()

    class Meta:
        model = PollOption
        fields = (
            "id",
            "text",
            "video_url",
            "video_file",
            "video_file_url",
            "order",
            "votes_count",
        )

    def get_video_file_url(self, obj):
        if not obj.video_file:
            return None

        request = self.context.get("request")
        video_url = obj.video_file.url

        if request:
            return request.build_absolute_uri(video_url)

        return video_url


class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)
    voting_open = serializers.BooleanField(source="is_open_for_voting", read_only=True)

    class Meta:
        model = Poll
        fields = (
            "id",
            "question",
            "description",
            "is_active",
            "voting_open",
            "starts_at",
            "ends_at",
            "created_at",
            "updated_at",
            "options",
        )


class PollCreateOptionSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=255)
    video_url = serializers.URLField(required=False, allow_blank=True, default="")
    video_file = serializers.FileField(required=False, allow_null=True)
    order = serializers.IntegerField(required=False, default=0)


class PollCreateSerializer(serializers.ModelSerializer):
    options = PollCreateOptionSerializer(many=True)

    class Meta:
        model = Poll
        fields = (
            "question",
            "description",
            "is_active",
            "starts_at",
            "ends_at",
            "options",
        )

    def validate_options(self, options):
        if len(options) < 2:
            raise serializers.ValidationError("Anketa musí mať aspoň 2 možnosti.")

        option_texts = [option["text"].strip().lower() for option in options]

        if len(option_texts) != len(set(option_texts)):
            raise serializers.ValidationError("Možnosti odpovedí sa nesmú opakovať.")

        return options

    def create(self, validated_data):
        options_data = validated_data.pop("options")

        poll = Poll.objects.create(**validated_data)

        for index, option_data in enumerate(options_data):
            PollOption.objects.create(
                poll=poll,
                text=option_data["text"],
                video_url=option_data.get("video_url", ""),
                video_file=option_data.get("video_file"),
                order=option_data.get("order", index),
            )

        return poll


class PollVoteSerializer(serializers.Serializer):
    option_id = serializers.IntegerField()

    def validate_option_id(self, option_id):
        poll = self.context.get("poll")

        if not poll:
            raise serializers.ValidationError("Anketa nebola nájdená.")

        option_exists = PollOption.objects.filter(
            id=option_id,
            poll=poll,
        ).exists()

        if not option_exists:
            raise serializers.ValidationError("Táto možnosť nepatrí k tejto ankete.")

        return option_id

from rest_framework import serializers

from apps.common.image_uploads import optimize_uploaded_image

from apps.clubs.models import Club
from apps.scraper.models import (
    ClubPlayer,
    SzfbCompetition,
    SzfbGoalieStat,
    SzfbMatch,
    SzfbMatchHistory,
    SzfbWatchAutoSyncConfig,
    SzfbPlayerStat,
    SzfbStandingRow,
    SzfbStandingZone,
    SzfbTeamBrand,
    SzfbTeamWatch,
    build_club_player_identity_key,
    normalize_player_name,
)
from apps.scraper.services.szfb_scraper import format_player_name
from apps.scraper.services.team_branding import (
    delete_team_brand_logo_if_unreferenced,
    resolve_team_brand,
)


class SzfbTeamBrandSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    display_name = serializers.CharField(source="team_name", read_only=True)
    shadow_color = serializers.SerializerMethodField()
    use_shadow_color = serializers.SerializerMethodField()
    branding_source_name = serializers.CharField(
        source="branding_source.team_name",
        read_only=True,
        allow_null=True,
    )
    competition_name = serializers.CharField(source="competition.name", read_only=True)
    competition_season = serializers.CharField(
        source="competition.season", read_only=True
    )
    branding_source_competition_name = serializers.CharField(
        source="branding_source.competition.name",
        read_only=True,
        allow_null=True,
    )
    own_logo_url = serializers.SerializerMethodField()
    own_shadow_color = serializers.CharField(source="shadow_color", read_only=True)
    own_use_shadow_color = serializers.BooleanField(
        source="use_shadow_color",
        read_only=True,
    )

    class Meta:
        model = SzfbTeamBrand
        fields = [
            "id",
            "team_name",
            "display_name",
            "competition",
            "competition_name",
            "competition_season",
            "szfb_competitor_id",
            "branding_source",
            "branding_source_name",
            "branding_source_competition_name",
            "logo_url",
            "shadow_color",
            "use_shadow_color",
            "own_logo_url",
            "own_shadow_color",
            "own_use_shadow_color",
            "is_active",
        ]

    def _get_logo_url(self, obj):
        if not obj.logo:
            return None

        try:
            logo_url = obj.logo.url
        except (OSError, ValueError):
            return None

        request = self.context.get("request")
        if request:
            try:
                return request.build_absolute_uri(logo_url)
            except Exception:
                return None

        return logo_url

    def get_logo_url(self, obj):
        return self._get_logo_url(obj.get_resolved_branding())

    def get_own_logo_url(self, obj):
        return self._get_logo_url(obj)

    def get_shadow_color(self, obj):
        return obj.get_resolved_branding().shadow_color

    def get_use_shadow_color(self, obj):
        return obj.get_resolved_branding().use_shadow_color


class TeamBrandResolvedMixin:
    def get_resolved_team_brand(
        self,
        team_name,
        competition_id=None,
        szfb_competitor_id=None,
        szfb_competition_id=None,
    ):
        brands = self.context.get("team_brands") or []
        brand = resolve_team_brand(
            team_name,
            brands,
            competition_id=competition_id,
            szfb_competitor_id=szfb_competitor_id,
            szfb_competition_id=szfb_competition_id,
        )

        if not brand:
            return None

        return SzfbTeamBrandSerializer(
            brand,
            context=self.context,
        ).data


class SzfbStandingRowSerializer(TeamBrandResolvedMixin, serializers.ModelSerializer):
    score = serializers.SerializerMethodField()
    team_brand = serializers.SerializerMethodField()

    def get_score(self, obj):
        if obj.goals_for is None or obj.goals_against is None:
            return None

        return f"{obj.goals_for}:{obj.goals_against}"

    def get_team_brand(self, obj):
        return self.get_resolved_team_brand(
            obj.team_name,
            competition_id=obj.competition_id,
            szfb_competitor_id=obj.szfb_competitor_id,
        )

    class Meta:
        model = SzfbStandingRow
        fields = [
            "position",
            "team_name",
            "szfb_competitor_id",
            "team_brand",
            "played",
            "goals_for",
            "goals_against",
            "score",
            "points",
        ]


class SzfbMatchSerializer(TeamBrandResolvedMixin, serializers.ModelSerializer):
    opponent_brand = serializers.SerializerMethodField()

    def get_opponent_brand(self, obj):
        return self.get_resolved_team_brand(
            obj.opponent,
            competition_id=obj.watched_team.competition_id,
        )

    class Meta:
        model = SzfbMatch
        fields = [
            "id",
            "match_type",
            "match_date",
            "match_time",
            "opponent",
            "opponent_brand",
            "venue",
            "result",
            "decision_type",
            "is_home",
        ]


class SzfbMatchHistorySerializer(TeamBrandResolvedMixin, serializers.ModelSerializer):
    match_type = serializers.SerializerMethodField()
    opponent_brand = serializers.SerializerMethodField()

    class Meta:
        model = SzfbMatchHistory
        fields = [
            "id",
            "match_type",
            "match_date",
            "match_time",
            "opponent",
            "opponent_brand",
            "venue",
            "result",
            "decision_type",
            "is_home",
        ]

    def get_match_type(self, _obj):
        return "finished"

    def get_opponent_brand(self, obj):
        return self.get_resolved_team_brand(
            obj.opponent,
            szfb_competition_id=obj.szfb_competition_id,
        )


class AdminSzfbTeamBrandWriteSerializer(serializers.Serializer):
    competition = serializers.PrimaryKeyRelatedField(
        queryset=SzfbCompetition.objects.all(),
        required=False,
    )
    team_name = serializers.CharField(required=False, max_length=255)
    szfb_competitor_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )
    branding_source = serializers.PrimaryKeyRelatedField(
        queryset=SzfbTeamBrand.objects.all(),
        required=False,
        allow_null=True,
    )
    logo = serializers.ImageField(required=False, allow_null=True)
    clear_logo = serializers.BooleanField(required=False, default=False)
    shadow_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={
            "invalid": "Farba musí byť HEX hodnota vo formáte #RRGGBB."
        },
    )
    use_shadow_color = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)

    def to_internal_value(self, data):
        normalized_data = data.copy()
        for field_name in ("szfb_competitor_id", "branding_source"):
            if normalized_data.get(field_name) == "":
                normalized_data[field_name] = None
        return super().to_internal_value(normalized_data)

    def validate(self, attrs):
        club = self.context.get("club")
        instance = getattr(self, "instance", None)

        if not club:
            raise serializers.ValidationError(
                {"club": "Klub nie je dostupný pre správu brandingu."}
            )

        team_name = attrs.get(
            "team_name",
            getattr(instance, "team_name", ""),
        ).strip()
        competition = attrs.get(
            "competition",
            getattr(instance, "competition", None),
        )

        if not team_name:
            raise serializers.ValidationError(
                {"team_name": "Presný názov tímu zo SZFB je povinný."}
            )
        if competition is None:
            raise serializers.ValidationError(
                {"competition": "Súťaž tímu je povinná."}
            )
        if not SzfbTeamWatch.objects.filter(
            club=club,
            competition=competition,
        ).exists():
            raise serializers.ValidationError(
                {"competition": "Táto súťaž nie je spravovaná daným klubom."}
            )

        szfb_competitor_id = attrs.get(
            "szfb_competitor_id",
            getattr(instance, "szfb_competitor_id", None),
        )
        duplicate = SzfbTeamBrand.objects.filter(
            club=club,
            competition=competition,
            team_name=team_name,
        )
        if instance:
            duplicate = duplicate.exclude(id=instance.id)

        if duplicate.exists():
            raise serializers.ValidationError(
                {"team_name": "Tento tím už v danej súťaži existuje."}
            )

        if szfb_competitor_id is not None:
            competitor_duplicate = SzfbTeamBrand.objects.filter(
                club=club,
                competition=competition,
                szfb_competitor_id=szfb_competitor_id,
            )
            if instance:
                competitor_duplicate = competitor_duplicate.exclude(id=instance.id)
            if competitor_duplicate.exists():
                raise serializers.ValidationError(
                    {"szfb_competitor_id": "Toto SZFB ID už v danej súťaži existuje."}
                )

        if instance and "team_name" in attrs and team_name != instance.team_name:
            raise serializers.ValidationError(
                {"team_name": "Názov tímu spravuje SZFB synchronizácia."}
            )
        if instance and "competition" in attrs and competition != instance.competition:
            raise serializers.ValidationError(
                {"competition": "Súťaž tímu spravuje SZFB synchronizácia."}
            )

        branding_source = attrs.get(
            "branding_source",
            getattr(instance, "branding_source", None),
        )
        if branding_source:
            if branding_source.club_id != club.id:
                raise serializers.ValidationError(
                    {"branding_source": "Zdroj brandingu musí patriť rovnakému klubu."}
                )
            if instance and branding_source.id == instance.id:
                raise serializers.ValidationError(
                    {"branding_source": "Tím nemôže prepojiť branding sám na seba."}
                )

            visited = {instance.id} if instance else set()
            source = branding_source
            while source:
                if source.id in visited:
                    raise serializers.ValidationError(
                        {"branding_source": "Prepojenie brandingu nesmie vytvoriť cyklus."}
                    )
                visited.add(source.id)
                source = source.branding_source

        attrs["team_name"] = team_name
        if "shadow_color" in attrs:
            attrs["shadow_color"] = (
                attrs["shadow_color"].upper() if attrs["shadow_color"] else None
            )
        use_shadow_color = attrs.get(
            "use_shadow_color",
            getattr(instance, "use_shadow_color", False),
        )
        shadow_color = attrs.get(
            "shadow_color",
            getattr(instance, "shadow_color", None),
        )
        if use_shadow_color and not shadow_color:
            raise serializers.ValidationError(
                {
                    "shadow_color": (
                        "Pre vynútenie manuálnej farby najprv vyber HEX farbu."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        club = self.context["club"]
        validated_data.pop("clear_logo", None)
        return SzfbTeamBrand.objects.create(club=club, **validated_data)

    def update(self, instance, validated_data):
        clear_logo = validated_data.pop("clear_logo", False)
        next_logo = validated_data.pop("logo", serializers.empty)

        if clear_logo and instance.logo:
            delete_team_brand_logo_if_unreferenced(instance)
            instance.logo = None

        if next_logo is not serializers.empty:
            if instance.logo:
                delete_team_brand_logo_if_unreferenced(instance)
            instance.logo = next_logo

        for field_name in [
            "competition",
            "branding_source",
            "shadow_color",
            "use_shadow_color",
            "is_active",
        ]:
            if field_name in validated_data:
                setattr(instance, field_name, validated_data[field_name])

        instance.save()
        return instance


class SzfbStandingZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = SzfbStandingZone
        fields = [
            "id",
            "kind",
            "label",
            "start_position",
            "end_position",
            "display_order",
            "is_active",
        ]


class SzfbTeamWatchSerializer(TeamBrandResolvedMixin, serializers.ModelSerializer):
    competition_name = serializers.CharField(source="competition.name", read_only=True)
    competition_season = serializers.CharField(source="competition.season", read_only=True)
    team_brand = serializers.SerializerMethodField()

    def get_team_brand(self, obj):
        return self.get_resolved_team_brand(
            obj.team_name,
            competition_id=obj.competition_id,
            szfb_competitor_id=obj.competitor_id,
        )

    class Meta:
        model = SzfbTeamWatch
        fields = [
            "id",
            "label",
            "team_name",
            "team_brand",
            "competition_name",
            "competition_season",
        ]


class PlayerProfileFieldsMixin(serializers.Serializer):
    club_player_id = serializers.SerializerMethodField()
    player_name = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    jersey_number = serializers.SerializerMethodField()
    display_position = serializers.SerializerMethodField()
    height_cm = serializers.SerializerMethodField()
    weight_kg = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_featured = serializers.SerializerMethodField()
    display_order = serializers.SerializerMethodField()

    def get_club_player(self, obj):
        return getattr(obj, "club_player", None)

    def get_club_player_id(self, obj):
        club_player = self.get_club_player(obj)

        if not club_player:
            return None

        return club_player.id

    def get_player_name(self, obj):
        club_player = self.get_club_player(obj)

        if club_player and club_player.full_name:
            return club_player.full_name

        return format_player_name(obj.player_name)

    def get_profile_photo(self, obj):
        club_player = self.get_club_player(obj)

        if club_player and club_player.photo:
            return club_player.photo

        legacy_photo = getattr(obj, "photo", None)
        if legacy_photo:
            return legacy_photo

        return None

    def get_safe_photo_url(self, photo):
        if not photo:
            return None

        try:
            if not photo.name or not photo.storage.exists(photo.name):
                return None

            return photo.url
        except (OSError, ValueError):
            return None

    def get_photo(self, obj):
        return self.get_safe_photo_url(self.get_profile_photo(obj))

    def get_photo_url(self, obj):
        photo_url = self.get_safe_photo_url(self.get_profile_photo(obj))

        if not photo_url:
            return None

        request = self.context.get("request")

        if request:
            try:
                return request.build_absolute_uri(photo_url)
            except Exception:
                return None

        return photo_url

    def get_jersey_number(self, obj):
        club_player = self.get_club_player(obj)

        if club_player and club_player.jersey_number is not None:
            return club_player.jersey_number

        return getattr(obj, "jersey_number", None)

    def get_display_position(self, obj):
        club_player = self.get_club_player(obj)

        if club_player and club_player.position:
            return club_player.position

        return getattr(obj, "player_position", "G")

    def get_height_cm(self, obj):
        club_player = self.get_club_player(obj)

        if club_player:
            return club_player.height_cm

        return None

    def get_weight_kg(self, obj):
        club_player = self.get_club_player(obj)

        if club_player:
            return club_player.weight_kg

        return None

    def get_bio(self, obj):
        club_player = self.get_club_player(obj)

        if club_player:
            return club_player.bio

        return getattr(obj, "bio", "")

    def get_is_active(self, obj):
        club_player = self.get_club_player(obj)

        if club_player:
            return club_player.is_active

        return getattr(obj, "is_active", True)

    def get_is_featured(self, obj):
        club_player = self.get_club_player(obj)

        if club_player:
            return club_player.is_featured

        return getattr(obj, "is_featured", False)

    def get_display_order(self, obj):
        club_player = self.get_club_player(obj)

        if club_player:
            return club_player.display_order

        return getattr(obj, "display_order", 0)


class SzfbPlayerStatSerializer(PlayerProfileFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = SzfbPlayerStat
        fields = [
            "id",
            "club_player_id",
            "szfb_player_id",
            "rank",
            "player_name",
            "birth_year",
            "team_short_name",
            "player_position",
            "games",
            "goals",
            "assists",
            "points",
            "points_avg",
            "esp",
            "ppp",
            "shp",
            "pim",
            "photo",
            "photo_url",
            "jersey_number",
            "display_position",
            "height_cm",
            "weight_kg",
            "bio",
            "is_active",
            "is_featured",
            "display_order",
        ]


class SzfbTeamWatchAdminSerializer(serializers.ModelSerializer):
    competition_id = serializers.IntegerField(source="competition.id", read_only=True)
    competition_name = serializers.CharField(source="competition.name", read_only=True)
    competition_season = serializers.CharField(source="competition.season", read_only=True)
    competition_source_url = serializers.CharField(
        source="competition.source_url",
        read_only=True,
    )
    club_id = serializers.IntegerField(source="club.id", read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)
    club_slug = serializers.CharField(source="club.slug", read_only=True)
    competition_last_synced_at = serializers.DateTimeField(
        source="competition.last_synced_at",
        read_only=True,
    )
    competition_sync_status = serializers.CharField(
        source="competition.sync_status",
        read_only=True,
    )
    competition_sync_started_at = serializers.DateTimeField(
        source="competition.sync_started_at",
        read_only=True,
    )
    competition_sync_finished_at = serializers.DateTimeField(
        source="competition.sync_finished_at",
        read_only=True,
    )
    competition_sync_error = serializers.CharField(
        source="competition.sync_error",
        read_only=True,
    )

    class Meta:
        model = SzfbTeamWatch
        fields = [
            "id",
            "label",
            "team_name",
            "competitor_id",
            "is_active",
            "competition_id",
            "competition_name",
            "competition_season",
            "competition_source_url",
            "club_id",
            "club_name",
            "club_slug",
            "competition_last_synced_at",
            "competition_sync_status",
            "competition_sync_started_at",
            "competition_sync_finished_at",
            "competition_sync_error",
        ]


class AdminSzfbStandingRowSerializer(TeamBrandResolvedMixin, serializers.ModelSerializer):
    score = serializers.SerializerMethodField()
    team_brand = serializers.SerializerMethodField()

    def get_score(self, obj):
        if obj.goals_for is None or obj.goals_against is None:
            return None

        return f"{obj.goals_for}:{obj.goals_against}"

    def get_team_brand(self, obj):
        return self.get_resolved_team_brand(
            obj.team_name,
            competition_id=obj.competition_id,
            szfb_competitor_id=obj.szfb_competitor_id,
        )

    class Meta:
        model = SzfbStandingRow
        fields = [
            "id",
            "position",
            "team_name",
            "szfb_competitor_id",
            "team_brand",
            "played",
            "goals_for",
            "goals_against",
            "score",
            "points",
        ]


class AdminSzfbMatchSerializer(TeamBrandResolvedMixin, serializers.ModelSerializer):
    opponent_brand = serializers.SerializerMethodField()

    def get_opponent_brand(self, obj):
        return self.get_resolved_team_brand(
            obj.opponent,
            competition_id=obj.watched_team.competition_id,
        )

    class Meta:
        model = SzfbMatch
        fields = [
            "id",
            "match_type",
            "match_date",
            "match_time",
            "opponent",
            "opponent_brand",
            "venue",
            "result",
            "decision_type",
            "is_home",
        ]


class AdminSzfbPlayerStatSerializer(PlayerProfileFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = SzfbPlayerStat
        fields = [
            "id",
            "club_player_id",
            "szfb_player_id",
            "rank",
            "player_name",
            "birth_year",
            "team_short_name",
            "player_position",
            "games",
            "goals",
            "assists",
            "points",
            "points_avg",
            "esp",
            "ppp",
            "shp",
            "pim",
            "photo",
            "photo_url",
            "jersey_number",
            "display_position",
            "height_cm",
            "weight_kg",
            "bio",
            "is_active",
            "is_featured",
            "display_order",
        ]


class AdminSzfbGoalieStatSerializer(
    PlayerProfileFieldsMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = SzfbGoalieStat
        fields = [
            "id",
            "club_player_id",
            "szfb_player_id",
            "rank",
            "jersey_number",
            "player_name",
            "birth_year",
            "games",
            "wins",
            "overtime_wins",
            "losses",
            "overtime_losses",
            "shots_against",
            "goals_against",
            "goals_against_average",
            "saves",
            "save_percentage",
            "minutes_played_seconds",
            "shutouts",
            "photo",
            "photo_url",
            "display_position",
            "height_cm",
            "weight_kg",
            "bio",
            "is_active",
            "is_featured",
            "display_order",
        ]


class AdminSzfbPlayerStatsOnlySerializer(serializers.ModelSerializer):
    player_name = serializers.SerializerMethodField()

    def get_player_name(self, obj):
        return format_player_name(obj.player_name)

    class Meta:
        model = SzfbPlayerStat
        fields = [
            "id",
            "szfb_player_id",
            "rank",
            "player_name",
            "birth_year",
            "team_short_name",
            "player_position",
            "games",
            "goals",
            "assists",
            "points",
            "points_avg",
            "esp",
            "ppp",
            "shp",
            "pim",
        ]


class AdminSzfbPlayerStatUpdateSerializer(serializers.Serializer):
    photo = serializers.ImageField(required=False, allow_null=True)
    clear_photo = serializers.BooleanField(required=False)

    jersey_number = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    player_position = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
    )
    height_cm = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    weight_kg = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    bio = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    is_featured = serializers.BooleanField(required=False)
    display_order = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def parse_optional_int(self, value, field_name):
        if value in ["", None]:
            return None

        try:
            parsed_value = int(value)
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError(
                {field_name: "Hodnota musí byť číslo."}
            ) from exc

        if parsed_value < 0:
            raise serializers.ValidationError(
                {field_name: "Hodnota nemôže byť záporná."}
            )

        return parsed_value

    def validate(self, attrs):
        optional_number_fields = [
            "jersey_number",
            "height_cm",
            "weight_kg",
            "display_order",
        ]

        for field_name in optional_number_fields:
            if field_name in attrs:
                attrs[field_name] = self.parse_optional_int(
                    attrs[field_name],
                    field_name,
                )

        if "photo" in attrs:
            attrs["photo"] = optimize_uploaded_image(
                attrs["photo"],
                "player",
                filename_prefix="player-photo",
            )

        return attrs

    def get_or_create_club_player(self, instance):
        if instance.club_player:
            return instance.club_player

        club = instance.watched_team.club if instance.watched_team else None

        if not club:
            raise serializers.ValidationError(
                {
                    "club_player": (
                        "Hráča nie je možné upraviť, pretože sledovaný tím nemá klub."
                    )
                }
            )

        identity_key = build_club_player_identity_key(
            instance.player_name,
            instance.birth_year,
        )

        club_player, _ = ClubPlayer.objects.get_or_create(
            club=club,
            identity_key=identity_key,
            defaults={
                "full_name": instance.player_name,
                "normalized_name": normalize_player_name(instance.player_name),
                "birth_year": instance.birth_year,
                "position": instance.player_position or "",
                "photo": instance.photo.name if instance.photo else "",
                "jersey_number": instance.jersey_number,
                "bio": instance.bio,
                "is_active": instance.is_active,
                "is_featured": instance.is_featured,
                "display_order": instance.display_order,
            },
        )

        instance.club_player = club_player
        instance.save(update_fields=["club_player"])

        return club_player

    def update(self, instance, validated_data):
        club_player = self.get_or_create_club_player(instance)

        clear_photo = validated_data.pop("clear_photo", False)

        if clear_photo:
            if club_player.photo:
                club_player.photo.delete(save=False)

            club_player.photo = None

        if "photo" in validated_data:
            club_player.photo = validated_data["photo"]

        if "jersey_number" in validated_data:
            club_player.jersey_number = validated_data["jersey_number"]

        if "player_position" in validated_data:
            club_player.position = validated_data["player_position"]

        if "height_cm" in validated_data:
            club_player.height_cm = validated_data["height_cm"]

        if "weight_kg" in validated_data:
            club_player.weight_kg = validated_data["weight_kg"]

        if "bio" in validated_data:
            club_player.bio = validated_data["bio"]

        if "is_active" in validated_data:
            club_player.is_active = validated_data["is_active"]

        if "is_featured" in validated_data:
            club_player.is_featured = validated_data["is_featured"]

        if "display_order" in validated_data:
            club_player.display_order = validated_data["display_order"] or 0

        club_player.save()

        instance.photo = club_player.photo.name if club_player.photo else ""
        instance.jersey_number = club_player.jersey_number
        instance.player_position = club_player.position or instance.player_position
        instance.bio = club_player.bio
        instance.is_active = club_player.is_active
        instance.is_featured = club_player.is_featured
        instance.display_order = club_player.display_order
        instance.save(
            update_fields=[
                "photo",
                "jersey_number",
                "player_position",
                "bio",
                "is_active",
                "is_featured",
                "display_order",
            ]
        )

        return instance


class AdminClubPlayerSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()

    class Meta:
        model = ClubPlayer
        fields = [
            "id",
            "full_name",
            "birth_year",
            "height_cm",
            "weight_kg",
            "photo_url",
            "jersey_number",
            "position",
            "bio",
            "is_active",
            "is_featured",
            "display_order",
            "categories",
        ]

    def get_photo_url(self, obj):
        photo = obj.photo

        if not photo or not photo.name:
            return None

        try:
            photo_url = photo.url
        except (OSError, ValueError):
            return None

        request = self.context.get("request")

        if request:
            try:
                return request.build_absolute_uri(photo_url)
            except Exception:
                return None

        return photo_url

    def get_categories(self, obj):
        categories = []
        seen_watch_ids = set()

        stats = (
            obj.szfb_stats
            .select_related("watched_team", "watched_team__competition")
            .all()
        )

        for stat in stats:
            watched_team = stat.watched_team

            if not watched_team or watched_team.id in seen_watch_ids:
                continue

            seen_watch_ids.add(watched_team.id)
            competition = watched_team.competition

            categories.append(
                {
                    "watch_id": watched_team.id,
                    "label": watched_team.label,
                    "team_name": watched_team.team_name,
                    "competition_id": competition.id if competition else None,
                    "competition_name": competition.name if competition else "",
                    "season": competition.season if competition else "",
                }
            )

        return sorted(
            categories,
            key=lambda item: (
                item["season"] or "",
                item["label"] or "",
                item["competition_name"] or "",
            ),
            reverse=True,
        )



class AdminClubPlayerUpdateSerializer(serializers.Serializer):
    photo = serializers.ImageField(required=False, allow_null=True)
    clear_photo = serializers.BooleanField(required=False)

    full_name = serializers.CharField(required=False, allow_blank=False, max_length=255)
    birth_year = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    jersey_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    position = serializers.CharField(required=False, allow_blank=True, max_length=50)
    height_cm = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    weight_kg = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    is_featured = serializers.BooleanField(required=False)
    display_order = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def parse_optional_int(self, value, field_name):
        if isinstance(value, str):
            value = value.strip()

        if value in ("", None):
            return None

        try:
            parsed_value = int(value)
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError(
                {field_name: "Hodnota musí byť číslo."}
            ) from exc

        if parsed_value < 0:
            raise serializers.ValidationError(
                {field_name: "Hodnota nemôže byť záporná."}
            )

        return parsed_value

    def parse_display_order(self, value):
        if isinstance(value, str):
            value = value.strip()

        if value in ("", None):
            return 0

        return self.parse_optional_int(value, "display_order")

    def normalize_uploaded_photo_name(self, uploaded_file):
        return optimize_uploaded_image(
            uploaded_file,
            "player",
            filename_prefix="club-player",
        )

    def validate(self, attrs):
        optional_number_fields = [
            "birth_year",
            "jersey_number",
            "height_cm",
            "weight_kg",
        ]

        for field_name in optional_number_fields:
            if field_name in attrs:
                attrs[field_name] = self.parse_optional_int(
                    attrs[field_name],
                    field_name,
                )

        if "display_order" in attrs:
            attrs["display_order"] = self.parse_display_order(
                attrs["display_order"]
            )

        if "photo" in attrs:
            attrs["photo"] = self.normalize_uploaded_photo_name(attrs["photo"])

        instance = getattr(self, "instance", None)

        if instance:
            next_full_name = attrs.get("full_name", instance.full_name)
            next_birth_year = attrs.get("birth_year", instance.birth_year)
            next_identity_key = build_club_player_identity_key(
                next_full_name,
                next_birth_year,
            )

            duplicate = (
                ClubPlayer.objects
                .filter(club=instance.club, identity_key=next_identity_key)
                .exclude(id=instance.id)
                .first()
            )

            if duplicate:
                raise serializers.ValidationError(
                    {
                        "full_name": (
                            "Hráč s rovnakým menom a rokom narodenia už "
                            "v tomto klube existuje."
                        )
                    }
                )

        return attrs

    def update(self, instance, validated_data):
        clear_photo = validated_data.pop("clear_photo", False)

        if clear_photo:
            if instance.photo:
                instance.photo.delete(save=False)

            instance.photo = None

        if "photo" in validated_data:
            instance.photo = validated_data["photo"]

        for field_name in [
            "full_name",
            "birth_year",
            "jersey_number",
            "position",
            "height_cm",
            "weight_kg",
            "bio",
            "is_active",
            "is_featured",
            "display_order",
        ]:
            if field_name in validated_data:
                value = validated_data[field_name]

                if field_name == "display_order" and value is None:
                    value = 0

                setattr(instance, field_name, value)

        instance.save()

        # Dočasne držíme staré polia v sezónnych štatistikách zosynchronizované,
        # aby sa nerozbil existujúci web ani existujúca stránka Športové dáta.
        update_fields = [
            "photo",
            "jersey_number",
            "player_position",
            "bio",
            "is_active",
            "is_featured",
            "display_order",
        ]

        for stat in instance.szfb_stats.all():
            stat.photo = instance.photo.name if instance.photo else ""
            stat.jersey_number = instance.jersey_number
            stat.player_position = instance.position or stat.player_position
            stat.bio = instance.bio
            stat.is_active = instance.is_active
            stat.is_featured = instance.is_featured
            stat.display_order = instance.display_order
            stat.save(update_fields=update_fields)

        return instance

    def create(self, validated_data):
        raise NotImplementedError("Tento serializer slúži iba na update.")


class AdminSzfbTeamWatchSummarySerializer(serializers.ModelSerializer):
    club_id = serializers.IntegerField(source="club.id", read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)
    club_slug = serializers.CharField(source="club.slug", read_only=True)
    matches_count = serializers.SerializerMethodField()
    finished_matches_count = serializers.SerializerMethodField()
    upcoming_matches_count = serializers.SerializerMethodField()
    player_stats_count = serializers.SerializerMethodField()
    goalie_stats_count = serializers.SerializerMethodField()

    def get_matches_count(self, obj):
        return getattr(obj, "matches_count", 0)

    def get_finished_matches_count(self, obj):
        return getattr(obj, "finished_matches_count", 0)

    def get_upcoming_matches_count(self, obj):
        return getattr(obj, "upcoming_matches_count", 0)

    def get_player_stats_count(self, obj):
        return getattr(obj, "player_stats_count", 0)

    def get_goalie_stats_count(self, obj):
        return getattr(obj, "goalie_stats_count", 0)

    class Meta:
        model = SzfbTeamWatch
        fields = [
            "id",
            "label",
            "team_name",
            "competitor_id",
            "is_active",
            "club_id",
            "club_name",
            "club_slug",
            "matches_count",
            "finished_matches_count",
            "upcoming_matches_count",
            "player_stats_count",
            "goalie_stats_count",
        ]


class AdminSzfbCompetitionSerializer(serializers.ModelSerializer):
    standings_count = serializers.SerializerMethodField()
    watched_teams_count = serializers.SerializerMethodField()
    watched_teams = serializers.SerializerMethodField()

    def get_club_slug(self):
        request = self.context.get("request")

        if not request:
            return ""

        return request.query_params.get("club", "")

    def get_standings_count(self, obj):
        return getattr(obj, "standings_count", 0)

    def get_watched_teams_count(self, obj):
        return getattr(obj, "watched_teams_count", 0)

    def get_watched_teams(self, obj):
        return AdminSzfbTeamWatchSummarySerializer(
            obj.watched_teams.all(),
            many=True,
        ).data

    class Meta:
        model = SzfbCompetition
        fields = [
            "id",
            "szfb_competition_id",
            "name",
            "season",
            "source_url",
            "standings_url",
            "results_url",
            "last_synced_at",
            "sync_status",
            "sync_started_at",
            "sync_finished_at",
            "sync_last_attempt_at",
            "sync_error",
            "standings_count",
            "watched_teams_count",
            "watched_teams",
        ]


class AdminSzfbWatchSettingsSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    competition_id = serializers.IntegerField(read_only=True)

    szfb_competition_id = serializers.IntegerField(min_value=1)
    competition_name = serializers.CharField(max_length=255)
    competition_season = serializers.CharField(
        max_length=50,
        allow_blank=True,
        required=False,
    )
    competition_source_url = serializers.URLField(allow_blank=True, required=False)
    standings_url = serializers.URLField(allow_blank=True, required=False)
    results_url = serializers.URLField(allow_blank=True, required=False)
    club_slug = serializers.CharField(required=False, allow_blank=True)

    label = serializers.CharField(max_length=255)
    team_name = serializers.CharField(max_length=255)
    competitor_id = serializers.IntegerField(
        min_value=1,
        allow_null=True,
        required=False,
    )
    is_active = serializers.BooleanField(required=False)

    def to_representation(self, instance):
        competition = instance.competition

        return {
            "id": instance.id,
            "competition_id": competition.id,
            "szfb_competition_id": competition.szfb_competition_id,
            "competition_name": competition.name,
            "competition_season": competition.season,
            "competition_source_url": competition.source_url,
            "standings_url": competition.standings_url,
            "results_url": competition.results_url,
            "club_slug": instance.club.slug if instance.club else "",
            "club_id": instance.club_id,
            "club_name": instance.club.name if instance.club else "",
            "label": instance.label,
            "team_name": instance.team_name,
            "competitor_id": instance.competitor_id,
            "is_active": instance.is_active,
        }

    def get_club_from_slug(self, club_slug):
        if not club_slug:
            return None

        try:
            return Club.objects.get(slug=club_slug)
        except Club.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"club_slug": "Klub s týmto slugom neexistuje."}
            ) from exc

    def validate(self, attrs):
        szfb_competition_id = attrs.get("szfb_competition_id")
        instance = getattr(self, "instance", None)

        if instance:
            duplicate = (
                SzfbCompetition.objects
                .filter(szfb_competition_id=szfb_competition_id)
                .exclude(id=instance.competition_id)
                .first()
            )

            if duplicate:
                raise serializers.ValidationError(
                    {
                        "szfb_competition_id": (
                            "Táto SZFB competition ID už existuje pri inej súťaži."
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
        szfb_competition_id = validated_data["szfb_competition_id"]
        club = self.get_club_from_slug(validated_data.get("club_slug", ""))

        competition, _ = SzfbCompetition.objects.update_or_create(
            szfb_competition_id=szfb_competition_id,
            defaults={
                "name": validated_data["competition_name"],
                "season": validated_data.get("competition_season", ""),
                "source_url": validated_data.get("competition_source_url", ""),
                "standings_url": validated_data.get("standings_url", ""),
                "results_url": validated_data.get("results_url", ""),
            },
        )

        return SzfbTeamWatch.objects.create(
            competition=competition,
            club=club,
            label=validated_data["label"],
            team_name=validated_data["team_name"],
            competitor_id=validated_data.get("competitor_id"),
            is_active=validated_data.get("is_active", True),
        )

    def update(self, instance, validated_data):
        competition = instance.competition

        competition.szfb_competition_id = validated_data["szfb_competition_id"]
        competition.name = validated_data["competition_name"]
        competition.season = validated_data.get("competition_season", "")
        competition.source_url = validated_data.get("competition_source_url", "")
        competition.standings_url = validated_data.get("standings_url", "")
        competition.results_url = validated_data.get("results_url", "")
        competition.save(
            update_fields=[
                "szfb_competition_id",
                "name",
                "season",
                "source_url",
                "standings_url",
                "results_url",
            ]
        )

        if "club_slug" in validated_data:
            instance.club = self.get_club_from_slug(
                validated_data.get("club_slug", "")
            )

        instance.label = validated_data["label"]
        instance.team_name = validated_data["team_name"]
        instance.competitor_id = validated_data.get("competitor_id")
        instance.is_active = validated_data.get("is_active", True)
        instance.save(
            update_fields=[
                "label",
                "team_name",
                "competitor_id",
                "is_active",
                "club",
            ]
        )

        return instance
class AdminSzfbWatchAutoSyncConfigSerializer(serializers.ModelSerializer):
    watch_id = serializers.IntegerField(source="watch.id", read_only=True)
    watch_label = serializers.CharField(source="watch.label", read_only=True)
    watch_is_active = serializers.BooleanField(source="watch.is_active", read_only=True)
    club_slug = serializers.CharField(source="watch.club.slug", read_only=True)
    club_name = serializers.CharField(source="watch.club.name", read_only=True)
    next_run_at_preview = serializers.SerializerMethodField()

    class Meta:
        model = SzfbWatchAutoSyncConfig
        fields = [
            "id",
            "watch_id",
            "watch_label",
            "watch_is_active",
            "club_slug",
            "club_name",
            "is_enabled",
            "frequency",
            "weekday",
            "run_time",
            "last_run_at",
            "next_run_at",
            "next_run_at_preview",
            "last_status",
            "last_message",
        ]
        read_only_fields = [
            "id",
            "watch_id",
            "watch_label",
            "watch_is_active",
            "club_slug",
            "club_name",
            "last_run_at",
            "next_run_at",
            "next_run_at_preview",
            "last_status",
            "last_message",
        ]

    def get_next_run_at_preview(self, obj):
        return obj.calculate_next_run_at()

    def validate_is_enabled(self, value):
        if value and not self.instance.watch.is_active:
            raise serializers.ValidationError(
                "Automatickú synchronizáciu nemožno zapnúť pre neaktívny tím."
            )
        return value

    def update(self, instance, validated_data):
        for field_name in [
            "is_enabled",
            "frequency",
            "weekday",
            "run_time",
        ]:
            if field_name in validated_data:
                setattr(instance, field_name, validated_data[field_name])

        instance.next_run_at = instance.calculate_next_run_at()
        instance.save(
            update_fields=[
                "is_enabled",
                "frequency",
                "weekday",
                "run_time",
                "next_run_at",
                "updated_at",
            ]
        )

        return instance

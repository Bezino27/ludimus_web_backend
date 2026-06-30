from rest_framework import serializers

from .models import Page, PageSection, PageSectionContactItem
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminPageSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageSection
        fields = [
            "id",
            "page",
            "section_type",
            "title",
            "pre_title",
            "order",
            "is_active",
            "hide_when_empty",
            "config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AdminPageSectionContactItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageSectionContactItem
        fields = [
            "id",
            "section",
            "contact_type",
            "value",
            "url",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AdminPageSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    public_path = serializers.CharField(source="get_public_path", read_only=True)
    team_category_name = serializers.SerializerMethodField()
    team_category_slug = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            "id",
            "club",
            "club_name",
            "title",
            "slug",
            "menu_title",
            "page_type",
            "is_homepage",
            "is_published",
            "show_in_header",
            "show_in_footer",
            "navigation_order",
            "menu_group",
            "menu_group_title",
            "team_category",
            "team_category_name",
            "team_category_slug",
            "public_path",
            "meta_title",
            "meta_description",
            "og_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "public_path",
            "team_category_name",
            "team_category_slug",
        ]

    def validate_club(self, club):
        request = self.context["request"]
        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            raise serializers.ValidationError("Nemáš oprávnenie pre tento klub.")
        return club

    def get_team_category_name(self, obj):
        if not obj.team_category:
            return None
        return obj.team_category.name

    def get_team_category_slug(self, obj):
        if not obj.team_category:
            return None
        return obj.team_category.slug

    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = self.instance
        page_type = attrs.get("page_type", getattr(instance, "page_type", None))
        club = attrs.get("club", getattr(instance, "club", None))
        team_category = attrs.get(
            "team_category",
            getattr(instance, "team_category", None),
        )

        if page_type == "category" and not team_category:
            raise serializers.ValidationError({
                "team_category": "Vyber napojenú tímovú kategóriu."
            })

        if page_type != "category":
            attrs["team_category"] = None
            return attrs

        if club and team_category and team_category.club_id != club.id:
            raise serializers.ValidationError({
                "team_category": "Napojená kategória musí patriť rovnakému klubu."
            })

        return attrs

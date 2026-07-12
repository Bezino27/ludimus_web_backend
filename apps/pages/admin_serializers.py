from rest_framework import serializers

from .models import Page, PageSection, PageSectionContactItem, PageSectionItem
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminPageSectionSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PageSection
        fields = [
            "id",
            "page",
            "section_type",
            "title",
            "pre_title",
            "content",
            "image",
            "image_url",
            "url",
            "file",
            "file_url",
            "order",
            "is_active",
            "hide_when_empty",
            "config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "image_url",
            "file_url",
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)

        return obj.image.url

    def get_file_url(self, obj):
        if not obj.file:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)

        return obj.file.url

    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = self.instance
        section_type = attrs.get(
            "section_type",
            getattr(instance, "section_type", None),
        )

        if section_type != "hero":
            attrs["image"] = None

        if section_type not in {"documents", "custom_documents"}:
            attrs["file"] = None

        if section_type not in {"links", "custom_links"}:
            attrs["url"] = ""

        return attrs


class AdminPageSectionItemSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    item_type = serializers.SerializerMethodField()
    section_type = serializers.CharField(source="section.section_type", read_only=True)

    class Meta:
        model = PageSectionItem
        fields = [
            "id",
            "section",
            "section_type",
            "title",
            "url",
            "file",
            "file_url",
            "item_type",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "file_url",
            "item_type",
            "section_type",
        ]

    def get_file_url(self, obj):
        if not obj.file:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)

        return obj.file.url

    def get_item_type(self, obj):
        if obj.section.section_type == "custom_documents":
            return "document"

        if obj.section.section_type == "custom_links":
            return "link"

        return "item"

    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = self.instance
        section = attrs.get("section", getattr(instance, "section", None))

        if not section:
            raise serializers.ValidationError({
                "section": "Vyber sekciu."
            })

        if section.section_type not in {"custom_documents", "custom_links"}:
            raise serializers.ValidationError({
                "section": (
                    "Položky môžeš pridávať iba k sekciám "
                    "Vlastné dokumenty alebo Vlastné odkazy."
                )
            })

        title = attrs.get("title", getattr(instance, "title", ""))
        url = attrs.get("url", getattr(instance, "url", ""))
        file = attrs.get("file", getattr(instance, "file", None))

        if not title:
            raise serializers.ValidationError({
                "title": "Vyplň názov položky."
            })

        if section.section_type == "custom_documents":
            attrs["url"] = ""

            if not file:
                raise serializers.ValidationError({
                    "file": "Pri vlastnom dokumente nahraj súbor."
                })

        if section.section_type == "custom_links":
            attrs["file"] = None

            if not url:
                raise serializers.ValidationError({
                    "url": "Pri vlastnom odkaze vyplň URL."
                })

        return attrs


class AdminPageSectionContactItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageSectionContactItem
        fields = [
            "id",
            "section",
            "contact_type",
            "label",
            "value",
            "url",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = self.instance
        section = attrs.get("section", getattr(instance, "section", None))
        contact_type = attrs.get(
            "contact_type",
            getattr(instance, "contact_type", "text"),
        )
        value = attrs.get("value", getattr(instance, "value", ""))
        url = attrs.get("url", getattr(instance, "url", ""))
        label = attrs.get("label", getattr(instance, "label", ""))

        if not section:
            raise serializers.ValidationError({
                "section": "Vyber kontaktnú sekciu."
            })

        if section.section_type != "contact":
            raise serializers.ValidationError({
                "section": "Kontaktné položky patria iba do kontaktnej sekcie."
            })

        if contact_type != "web":
            attrs["url"] = ""
            url = ""

        if not value and not url:
            raise serializers.ValidationError({
                "value": "Vyplň hodnotu alebo URL kontaktnej položky."
            })

        if not label:
            labels_by_type = dict(PageSectionContactItem.CONTACT_TYPE_CHOICES)
            attrs["label"] = labels_by_type.get(contact_type, "Kontakt")

        return attrs


class AdminPageSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    public_path = serializers.CharField(source="get_public_path", read_only=True)
    is_deletable = serializers.BooleanField(read_only=True)
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
            "is_deletable",
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
            "is_deletable",
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

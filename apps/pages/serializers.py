from rest_framework import serializers

from .models import Page, PageSection, PageSectionContactItem, PageSectionItem


class PageSectionItemSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    item_type = serializers.SerializerMethodField()

    class Meta:
        model = PageSectionItem
        fields = [
            "id",
            "title",
            "url",
            "file",
            "file_url",
            "item_type",
            "order",
            "is_active",
        ]

    def get_file_url(self, obj):
        if not obj.file:
            return None

        request = self.context.get("request")
        file_url = obj.file.url

        if request:
            return request.build_absolute_uri(file_url)

        return file_url

    def get_item_type(self, obj):
        if obj.section.section_type == "custom_documents":
            return "document"

        if obj.section.section_type == "custom_links":
            return "link"

        return "item"


class PageSectionContactItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageSectionContactItem
        fields = [
            "id",
            "contact_type",
            "value",
            "url",
            "order",
            "is_active",
        ]


class PageSectionSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    contact_items = serializers.SerializerMethodField()

    class Meta:
        model = PageSection
        fields = [
            "id",
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
            "items",
            "contact_items",
        ]

    def get_file_url(self, obj):
        if not obj.file:
            return None

        request = self.context.get("request")
        file_url = obj.file.url

        if request:
            return request.build_absolute_uri(file_url)

        return file_url

    def get_image_url(self, obj):
        if not obj.image:
            return None

        request = self.context.get("request")
        image_url = obj.image.url

        if request:
            return request.build_absolute_uri(image_url)

        return image_url

    def get_items(self, obj):
        items = obj.items.filter(is_active=True).order_by("order", "id")
        return PageSectionItemSerializer(items, many=True, context=self.context).data

    def get_contact_items(self, obj):
        items = obj.contact_items.filter(is_active=True).order_by("order", "id")
        return PageSectionContactItemSerializer(
            items,
            many=True,
            context=self.context,
        ).data


class PageSerializer(serializers.ModelSerializer):
    club_slug = serializers.CharField(source="club.slug", read_only=True)
    public_path = serializers.CharField(source="get_public_path", read_only=True)
    sections = serializers.SerializerMethodField()
    team_category = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            "id",
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
            "public_path",
            "meta_title",
            "meta_description",
            "og_image",
            "club_slug",
            "sections",
            "created_at",
            "updated_at",
        ]

    def get_sections(self, obj):
        sections = obj.sections.filter(is_active=True).order_by("order", "id")
        return PageSectionSerializer(sections, many=True, context=self.context).data

    def get_team_category(self, obj):
        category = obj.team_category

        if not category:
            return None

        return {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "category_subname": category.category_subname,
            "league_name": category.league_name,
        }

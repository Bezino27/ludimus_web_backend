from rest_framework import serializers

from .models import Page, PageSection


class PageSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageSection
        fields = [
            "id",
            "section_type",
            "title",
            "pre_title",
            "order",
            "is_active",
            "hide_when_empty",
            "config",
        ]


class PageSerializer(serializers.ModelSerializer):
    club_slug = serializers.CharField(source="club.slug", read_only=True)
    sections = serializers.SerializerMethodField()

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

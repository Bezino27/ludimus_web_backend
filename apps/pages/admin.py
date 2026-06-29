from django import forms
from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html

from .models import (
    Page,
    PageSection,
    PageSectionContactItem,
    PageSectionItem,
    SECTION_CHOICES_BY_PAGE_TYPE,
)


# # PAGE SECTION FORM

class PageSectionForm(forms.ModelForm):
    class Meta:
        model = PageSection
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        page = None

        if self.instance and self.instance.pk:
            page = self.instance.page
        elif self.initial.get("page"):
            try:
                page = Page.objects.get(pk=self.initial.get("page"))
            except Page.DoesNotExist:
                page = None
        elif self.data.get("page"):
            try:
                page = Page.objects.get(pk=self.data.get("page"))
            except (Page.DoesNotExist, ValueError, TypeError):
                page = None

        if page:
            allowed = SECTION_CHOICES_BY_PAGE_TYPE.get(page.page_type, [])
            self.fields["section_type"].choices = [
                ("", "---------"),
                *[
                    choice
                    for choice in PageSection.SECTION_TYPE_CHOICES
                    if choice[0] in allowed
                ],
            ]


# # PAGE INLINE FILTER

class PageSectionInlineFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)

        page = self.instance

        if not page or not page.pk:
            return

        allowed = SECTION_CHOICES_BY_PAGE_TYPE.get(page.page_type, [])

        if "section_type" in form.fields and allowed:
            form.fields["section_type"].choices = [
                ("", "---------"),
                *[
                    choice
                    for choice in PageSection.SECTION_TYPE_CHOICES
                    if choice[0] in allowed
                ],
            ]


class PageSectionInline(admin.TabularInline):
    model = PageSection
    formset = PageSectionInlineFormSet
    extra = 0
    show_change_link = True

    fields = [
        "section_type",
        "pre_title",
        "title",
        "order",
        "is_active",
        "hide_when_empty",
    ]

    ordering = ["order", "id"]


# # SECTION ITEMS INLINES

class CustomLinkItemInline(admin.TabularInline):
    model = PageSectionItem
    extra = 1
    fields = [
        "title",
        "url",
        "order",
        "is_active",
    ]
    ordering = ["order", "id"]
    verbose_name = "Vlastný odkaz"
    verbose_name_plural = "Vlastné odkazy"


class CustomDocumentItemInline(admin.TabularInline):
    model = PageSectionItem
    extra = 1
    fields = [
        "title",
        "file",
        "order",
        "is_active",
    ]
    ordering = ["order", "id"]
    verbose_name = "Vlastný dokument"
    verbose_name_plural = "Vlastné dokumenty"


class ContactItemInline(admin.TabularInline):
    model = PageSectionContactItem
    extra = 1
    fields = [
        "contact_type",
        "value",
        "url",
        "order",
        "is_active",
    ]
    ordering = ["order", "id"]
    verbose_name = "Kontaktná položka"
    verbose_name_plural = "Kontaktné položky"


# # PAGE ADMIN

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "club",
        "page_type",
        "public_path_preview",
        "menu_group",
        "show_in_header",
        "show_in_footer",
        "is_published",
        "navigation_order",
    ]

    list_filter = [
        "club",
        "page_type",
        "menu_group",
        "show_in_header",
        "show_in_footer",
        "is_published",
    ]

    search_fields = [
        "title",
        "slug",
        "menu_title",
        "club__name",
    ]

    prepopulated_fields = {
        "slug": ["title"],
    }

    ordering = [
        "club",
        "navigation_order",
        "title",
    ]

    inlines = [
        PageSectionInline,
    ]

    fieldsets = (
        (
            "Základné údaje",
            {
                "fields": (
                    "club",
                    "title",
                    "slug",
                    "page_type",
                    "is_homepage",
                    "is_published",
                )
            },
        ),
        (
            "Menu / navigácia",
            {
                "fields": (
                    "menu_title",
                    "show_in_header",
                    "show_in_footer",
                    "navigation_order",
                    "menu_group",
                    "menu_group_title",
                )
            },
        ),
        (
            "SEO",
            {
                "classes": ("collapse",),
                "fields": (
                    "meta_title",
                    "meta_description",
                    "og_image",
                ),
            },
        ),
    )

    def public_path_preview(self, obj):
        if not obj.pk:
            return "-"

        return format_html("<code>{}</code>", obj.get_public_path())

    public_path_preview.short_description = "URL"


# # PAGE SECTION ADMIN

@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    form = PageSectionForm

    list_display = [
        "section_label",
        "page",
        "section_type",
        "title",
        "items_count",
        "order",
        "is_active",
    ]

    list_filter = [
        "section_type",
        "is_active",
        "page__club",
        "page",
    ]

    search_fields = [
        "title",
        "pre_title",
        "content",
        "page__title",
        "page__slug",
    ]

    ordering = [
        "page__club__name",
        "page__title",
        "order",
        "id",
    ]

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []

        if obj.section_type == "custom_links":
            return [CustomLinkItemInline(self.model, self.admin_site)]

        if obj.section_type == "custom_documents":
            return [CustomDocumentItemInline(self.model, self.admin_site)]

        if obj.section_type == "contact":
            return [ContactItemInline(self.model, self.admin_site)]

        return []

    def get_fieldsets(self, request, obj=None):
        basic_fields = (
            "page",
            "section_type",
            "pre_title",
            "title",
            "order",
            "is_active",
            "hide_when_empty",
        )

        if not obj:
            return (
                (
                    "Základ sekcie",
                    {
                        "fields": basic_fields,
                    },
                ),
            )

        if obj.section_type in {"custom_links", "custom_documents"}:
            return (
                (
                    "Základ sekcie",
                    {
                        "fields": basic_fields,
                    },
                ),
            )

        if obj.section_type == "hero":
            return (
                (
                    "Základ sekcie",
                    {
                        "fields": (
                            "page",
                            "section_type",
                            "pre_title",
                            "title",
                            "order",
                            "is_active",
                            "hide_when_empty",
                        ),
                    },
                ),
                (
                    "Hero obrázok",
                    {
                        "fields": (
                            "image",
                        ),
                    },
                ),
            )

        if obj.section_type == "custom_text":
            return (
                (
                    "Základ sekcie",
                    {
                        "fields": basic_fields,
                    },
                ),
                (
                    "Text sekcie",
                    {
                        "fields": (
                            "content",
                        ),
                    },
                ),
            )

        if obj.section_type == "gallery":
            return (
                (
                    "Základ sekcie",
                    {
                        "fields": basic_fields,
                    },
                ),
                (
                    "Galéria",
                    {
                        "fields": (
                            "content",
                            "image",
                            "config",
                        ),
                    },
                ),
            )

        if obj.section_type == "links":
            return (
                (
                    "Základ sekcie",
                    {
                        "fields": basic_fields,
                    },
                ),
                (
                    "Klubové odkazy",
                    {
                        "fields": (
                            "config",
                        ),
                    },
                ),
            )

        if obj.section_type == "documents":
            return (
                (
                    "Základ sekcie",
                    {
                        "fields": basic_fields,
                    },
                ),
                (
                    "Klubové dokumenty",
                    {
                        "fields": (
                            "config",
                        ),
                    },
                ),
            )

        return (
            (
                "Základ sekcie",
                {
                    "fields": basic_fields,
                },
            ),
            (
                "Pokročilé nastavenia",
                {
                    "classes": ("collapse",),
                    "fields": (
                        "content",
                        "image",
                        "url",
                        "file",
                        "config",
                    ),
                },
            ),
        )

    def section_label(self, obj):
        return str(obj)

    section_label.short_description = "Sekcia"

    def items_count(self, obj):
        return obj.items.count()

    items_count.short_description = "Položky"


# # PAGE SECTION ITEM ADMIN

@admin.register(PageSectionItem)
class PageSectionItemAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "section",
        "section_type",
        "page",
        "item_preview",
        "order",
        "is_active",
    ]

    list_filter = [
        "is_active",
        "section__section_type",
        "section__page__club",
        "section__page",
    ]

    search_fields = [
        "title",
        "url",
        "section__title",
        "section__page__title",
        "section__page__slug",
    ]

    ordering = [
        "section__page__club__name",
        "section__page__title",
        "section__order",
        "order",
        "id",
    ]

    fields = [
        "section",
        "title",
        "url",
        "file",
        "order",
        "is_active",
    ]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        section_field = form.base_fields.get("section")
        if section_field:
            section_field.queryset = PageSection.objects.filter(
                section_type__in=["custom_documents", "custom_links"]
            ).select_related("page", "page__club")

        return form

    def section_type(self, obj):
        return obj.section.get_section_type_display()

    section_type.short_description = "Typ sekcie"

    def page(self, obj):
        return obj.section.page

    page.short_description = "Stránka"

    def item_preview(self, obj):
        if obj.url:
            return obj.url

        if obj.file:
            return obj.file.name

        return "-"

    item_preview.short_description = "URL / súbor"
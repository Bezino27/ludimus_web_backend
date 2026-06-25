from copy import deepcopy

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    Page,
    PageSection,
    SECTION_CHOICES_BY_PAGE_TYPE,
    create_default_page_sections,
)
from .revalidation import revalidate_page, revalidate_page_section


YOUTH_PAGE_TARGETS = [
    {
        "title": "Mladší žiaci",
        "slug": "mladsi-ziaci",
        "menu_title": "Mladší žiaci",
        "navigation_order": 2,
    },
    {
        "title": "Starší žiaci",
        "slug": "starsi-ziaci",
        "menu_title": "Starší žiaci",
        "navigation_order": 3,
    },
]


def get_allowed_section_choices(page):
    if not page:
        return PageSection.SECTION_TYPE_CHOICES

    allowed_values = SECTION_CHOICES_BY_PAGE_TYPE.get(page.page_type)

    if not allowed_values:
        return PageSection.SECTION_TYPE_CHOICES

    return [
        choice
        for choice in PageSection.SECTION_TYPE_CHOICES
        if choice[0] in allowed_values
    ]


class PageSectionInline(admin.TabularInline):
    model = PageSection
    extra = 0
    fields = (
        "section_type",
        "pre_title",
        "title",
        "order",
        "is_active",
        "hide_when_empty",
    )

    def get_formset(self, request, obj=None, **kwargs):
        request._page_section_inline_page = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "section_type":
            page = getattr(request, "_page_section_inline_page", None)

            if not page:
                object_id = request.resolver_match.kwargs.get("object_id")

                if object_id:
                    try:
                        page = Page.objects.get(pk=object_id)
                    except Page.DoesNotExist:
                        page = None

            if page:
                kwargs["choices"] = get_allowed_section_choices(page)
            else:
                kwargs["choices"] = get_default_section_choices()

        return super().formfield_for_choice_field(db_field, request, **kwargs)


def get_section_page_from_request(request):
    object_id = request.resolver_match.kwargs.get("object_id")

    if object_id:
        try:
            section = PageSection.objects.select_related("page").get(pk=object_id)
            return section.page
        except PageSection.DoesNotExist:
            return None

    page_id = request.GET.get("page")

    if page_id:
        try:
            return Page.objects.get(pk=page_id)
        except Page.DoesNotExist:
            return None

    return None


def get_default_section_choices():
    allowed_values = SECTION_CHOICES_BY_PAGE_TYPE["category"]

    return [
        choice
        for choice in PageSection.SECTION_TYPE_CHOICES
        if choice[0] in allowed_values
    ]


def copy_sections_from_page(source_page, target_page):
    if target_page.sections.exists():
        return False

    source_sections = list(source_page.sections.order_by("order", "id"))

    if not source_sections:
        return False

    PageSection.objects.bulk_create(
        PageSection(
            page=target_page,
            section_type=section.section_type,
            pre_title=section.pre_title,
            title=section.title,
            order=section.order,
            is_active=section.is_active,
            hide_when_empty=section.hide_when_empty,
            config=deepcopy(section.config),
        )
        for section in source_sections
    )
    return True


class PageSectionAdminMixin:
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "section_type":
            page = get_section_page_from_request(request)

            if page:
                kwargs["choices"] = get_allowed_section_choices(page)
            else:
                kwargs["choices"] = get_default_section_choices()

        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "page":
            page = get_section_page_from_request(request)

            if page:
                kwargs["initial"] = page.pk

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "club",
        "page_type",
        "slug",
        "public_path",
        "menu_group",
        "navigation_order",
        "is_published",
        "show_in_footer",
    )
    list_filter = (
        "club",
        "page_type",
        "menu_group",
        "is_published",
        "show_in_footer",
    )
    search_fields = ("title", "menu_title", "slug", "club__name")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = (
        "public_path",
        "default_sections_button",
        "copy_youth_pages_button",
    )
    inlines = [PageSectionInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/create-default-sections/",
                self.admin_site.admin_view(self.create_default_sections_view),
                name="pages_page_create_default_sections",
            ),
            path(
                "<path:object_id>/copy-youth-pages/",
                self.admin_site.admin_view(self.copy_youth_pages_view),
                name="pages_page_copy_youth_pages",
            ),
        ]
        return custom_urls + urls

    def create_default_sections_view(self, request, object_id):
        page = self.get_object(request, object_id)

        if not page:
            self.message_user(
                request,
                "Stránka neexistuje.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect("../")

        if create_default_page_sections(page):
            self.message_user(
                request,
                "Default sekcie boli vytvorené.",
                level=messages.SUCCESS,
            )
            revalidate_page(page, reason="Default PageSections created in Django admin")
        else:
            self.message_user(
                request,
                "Default sekcie sa nevytvorili. Stránka už má sekcie alebo pre tento typ stránky nie je dostupná šablóna.",
                level=messages.WARNING,
            )

        return HttpResponseRedirect("../change/")

    def copy_youth_pages_view(self, request, object_id):
        source_page = self.get_object(request, object_id)

        if not source_page:
            self.message_user(
                request,
                "Zdrojová stránka neexistuje.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect("../")

        if source_page.slug != "pripravka":
            self.message_user(
                request,
                "Tento button používaj na stránke Prípravka.",
                level=messages.WARNING,
            )
            return HttpResponseRedirect("../change/")

        created_pages = []
        reused_pages = []
        copied_sections = []

        for target in YOUTH_PAGE_TARGETS:
            target_page, created = Page.objects.get_or_create(
                club=source_page.club,
                slug=target["slug"],
                defaults={
                    "title": target["title"],
                    "menu_title": target["menu_title"],
                    "page_type": source_page.page_type,
                    "is_homepage": False,
                    "is_published": source_page.is_published,
                    "show_in_footer": source_page.show_in_footer,
                    "navigation_order": target["navigation_order"],
                    "menu_group": source_page.menu_group,
                    "menu_group_title": source_page.menu_group_title or "Mládež",
                    "meta_title": target["title"],
                    "meta_description": source_page.meta_description,
                    "og_image": source_page.og_image,
                },
            )

            if created:
                created_pages.append(target_page.title)
            else:
                reused_pages.append(target_page.title)

            if copy_sections_from_page(source_page, target_page):
                copied_sections.append(target_page.title)

            revalidate_page(target_page, reason="Youth Page copied from Pripravka in Django admin")

        details = []

        if created_pages:
            details.append(f"Vytvorené stránky: {', '.join(created_pages)}.")

        if reused_pages:
            details.append(f"Už existovali: {', '.join(reused_pages)}.")

        if copied_sections:
            details.append(f"Skopírované sekcie: {', '.join(copied_sections)}.")

        if not details:
            details.append("Nevznikli žiadne nové zmeny.")

        self.message_user(request, " ".join(details), level=messages.SUCCESS)
        return HttpResponseRedirect("../change/")

    @admin.display(description="Default sekcie")
    def default_sections_button(self, obj):
        if not obj.pk:
            return "Najprv ulož stránku."

        url = reverse(
            "admin:pages_page_create_default_sections",
            args=[obj.pk],
        )

        return format_html(
            '<a class="button" href="{}">Vytvoriť default sekcie</a>',
            url,
        )

    @admin.display(description="Mládežnícke stránky")
    def copy_youth_pages_button(self, obj):
        if not obj.pk:
            return "Najprv ulož stránku."

        if obj.slug != "pripravka":
            return "Dostupné iba na stránke Prípravka."

        url = reverse(
            "admin:pages_page_copy_youth_pages",
            args=[obj.pk],
        )

        return format_html(
            '<a class="button" href="{}">Vytvoriť mladších a starších žiakov podľa Prípravky</a>',
            url,
        )

    @admin.display(description="Verejná URL")
    def public_path(self, obj):
        if not obj.pk:
            return "Uložiť stránku pre výpočet URL"

        return obj.get_public_path()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        revalidate_page(obj, reason="Page saved in Django admin")

    def delete_model(self, request, obj):
        page = obj
        super().delete_model(request, obj)
        revalidate_page(page, reason="Page deleted in Django admin")

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        deleted_objects = list(formset.deleted_objects)

        for obj in deleted_objects:
            obj.delete()

        for instance in instances:
            instance.save()

        formset.save_m2m()

        if formset.model is PageSection:
            revalidate_page(form.instance, reason="Page sections saved in Django admin")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if create_default_page_sections(form.instance):
            revalidate_page(
                form.instance,
                reason="Default PageSections created in Django admin",
            )

    fieldsets = (
        (
            "Základné údaje",
            {
                "fields": (
                    "club",
                    "title",
                    "slug",
                    "menu_title",
                    "page_type",
                    "public_path",
                    "default_sections_button",
                    "copy_youth_pages_button",
                    "is_homepage",
                    "is_published",
                )
            },
        ),
        (
            "Navigácia",
            {
                "fields": (
                    "menu_group",
                    "menu_group_title",
                    "show_in_footer",
                    "navigation_order",
                )
            },
        ),
        (
            "SEO",
            {
                "fields": (
                    "meta_title",
                    "meta_description",
                    "og_image",
                )
            },
        ),
    )


@admin.register(PageSection)
class PageSectionAdmin(PageSectionAdminMixin, admin.ModelAdmin):
    list_display = (
        "page",
        "section_type",
        "title",
        "order",
        "is_active",
        "hide_when_empty",
    )
    list_filter = (
        "section_type",
        "is_active",
        "hide_when_empty",
        "page__club",
    )
    search_fields = (
        "page__title",
        "title",
    )
    ordering = (
        "page__club",
        "page",
        "order",
    )
    fields = (
        "page",
        "section_type",
        "pre_title",
        "title",
        "order",
        "is_active",
        "hide_when_empty",
    )


    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        revalidate_page_section(obj, reason="PageSection saved in Django admin")

    def delete_model(self, request, obj):
        section = obj
        super().delete_model(request, obj)
        revalidate_page_section(section, reason="PageSection deleted in Django admin")

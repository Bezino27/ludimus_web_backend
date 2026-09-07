from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.clubs.models import Club, ClubMembership
from apps.pages.admin_serializers import AdminPageSerializer
from apps.pages.admin import PageAdmin
from apps.pages.models import Page
from apps.pages.revalidation import get_page_revalidation_paths
from apps.pages.serializers import PageSerializer
from apps.teams.models import Category


class PageTeamCategoryTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="ATU Košice", slug="atu-kosice")
        self.category = Category.objects.create(
            club=self.club,
            name="Prípravka",
            slug="pripravka",
            season="2026/2027",
            birth_year_from=2016,
            birth_year_to=2018,
            category_subname="U11-U9",
            league_name="Liga prípraviek",
        )
        self.user = get_user_model().objects.create_user(
            username="editor",
            password="password",
        )
        ClubMembership.objects.create(
            user=self.user,
            club=self.club,
            role="editor",
            is_active=True,
        )

    def _request(self):
        request = APIRequestFactory().post("/api/admin/pages/")
        request.user = self.user
        return request

    def test_category_page_uses_page_slug_for_public_path(self):
        page = Page.objects.create(
            club=self.club,
            title="Elevovia",
            slug="elevovia",
            page_type="category",
            team_category=self.category,
        )

        self.assertEqual(page.get_public_path(), "/kategorie/elevovia")

    def test_admin_serializer_requires_team_category_for_category_page(self):
        serializer = AdminPageSerializer(
            data={
                "club": self.club.id,
                "title": "Elevovia",
                "slug": "elevovia",
                "page_type": "category",
            },
            context={"request": self._request()},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("team_category", serializer.errors)

    def test_public_serializer_returns_linked_team_category(self):
        page = Page.objects.create(
            club=self.club,
            title="Elevovia",
            slug="elevovia",
            page_type="category",
            team_category=self.category,
        )

        data = PageSerializer(page).data

        self.assertEqual(data["team_category"]["id"], self.category.id)
        self.assertEqual(data["team_category"]["slug"], "pripravka")
        self.assertEqual(data["team_category"]["name"], "Prípravka")

    def test_page_paths_include_old_new_slug_and_sitemap(self):
        page = Page.objects.create(
            club=self.club, title="Nová", slug="nova", page_type="custom"
        )
        self.assertEqual(
            get_page_revalidation_paths(page, old_path="/stranka/stara"),
            ["/stranka/nova", "/stranka/stara", "/sitemap.xml"],
        )

    @patch("apps.pages.admin.revalidate_page")
    def test_page_django_admin_schedules_revalidation(self, revalidate_page):
        page = Page.objects.create(
            club=self.club, title="Stránka", slug="stranka", page_type="custom"
        )
        page.slug = "nova-stranka"
        PageAdmin(Page, admin.site).save_model(None, page, None, True)
        revalidate_page.assert_called_once_with(
            page,
            reason="Page saved in Django admin",
            old_path="/stranka/stranka",
        )

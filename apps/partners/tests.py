from unittest.mock import patch

from django.test import TestCase

from apps.clubs.models import Club
from apps.partners.models import Partner
from apps.partners.revalidation import revalidate_partner_paths


class PartnerRevalidationTests(TestCase):
    @patch("apps.partners.revalidation.schedule_revalidation")
    def test_partner_uses_on_commit_scheduler(self, schedule_revalidation):
        club = Club.objects.create(name="ATU", slug="atu")
        revalidate_partner_paths(Partner(club=club), "Partner saved")
        schedule_revalidation.assert_called_once_with(
            ["/"], reason="Partner saved", club_slug="atu"
        )

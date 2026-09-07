from unittest.mock import patch

from django.db import transaction
from django.test import TestCase, TransactionTestCase

from apps.common.revalidation import schedule_revalidation


class ScheduleRevalidationTests(TestCase):
    @patch("apps.common.revalidation.revalidate_paths")
    def test_runs_only_after_commit_and_deduplicates_paths(self, revalidate_paths):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            scheduled = schedule_revalidation(
                ["/kategorie/muzi", "", "invalid", "/kategorie/muzi"],
                reason="test",
            )

        self.assertTrue(scheduled)
        revalidate_paths.assert_not_called()
        self.assertEqual(len(callbacks), 1)

        callbacks[0]()

        revalidate_paths.assert_called_once_with(
            ["/kategorie/muzi"],
            reason="test",
            club_slug="",
        )

    @patch(
        "apps.common.revalidation.revalidate_paths",
        side_effect=RuntimeError("revalidation failed"),
    )
    def test_unexpected_exception_does_not_escape_callback(self, revalidate_paths):
        with self.captureOnCommitCallbacks(execute=True):
            schedule_revalidation(["/kategorie/muzi"], reason="test")

        revalidate_paths.assert_called_once()


class ScheduleRevalidationRollbackTests(TransactionTestCase):
    @patch("apps.common.revalidation.revalidate_paths")
    def test_does_not_run_after_rollback(self, revalidate_paths):
        try:
            with transaction.atomic():
                schedule_revalidation(["/kategorie/muzi"], reason="test")
                raise RuntimeError("rollback")
        except RuntimeError:
            pass

        revalidate_paths.assert_not_called()

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.posts.models import Post


class Command(BaseCommand):
    help = "Backfill missing width and height metadata for post featured images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Read and report image dimensions without updating the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        posts_with_images = Post.objects.exclude(featured_image="").exclude(
            featured_image__isnull=True
        )
        candidates = posts_with_images.filter(
            Q(image_width__isnull=True) | Q(image_height__isnull=True)
        ).only("id", "featured_image", "image_width", "image_height")

        found = posts_with_images.count()
        pending = candidates.count()
        already_populated = found - pending
        updated = 0
        failed = 0

        self.stdout.write(
            f"Found {found} post image(s): {already_populated} already populated, "
            f"{pending} pending."
        )

        for post in candidates.iterator():
            try:
                width, height = post.read_featured_image_dimensions()
            except Exception as exc:
                failed += 1
                self.stderr.write(
                    self.style.WARNING(
                        f"Post {post.pk} ({post.featured_image.name}): "
                        f"{type(exc).__name__}: {exc}"
                    )
                )
                continue

            if not width or not height:
                failed += 1
                self.stderr.write(
                    self.style.WARNING(
                        f"Post {post.pk} ({post.featured_image.name}): "
                        "image has no valid dimensions"
                    )
                )
                continue

            updated += 1

            if not dry_run:
                Post.objects.filter(pk=post.pk).update(
                    image_width=width,
                    image_height=height,
                )

            prefix = "Would update" if dry_run else "Updated"
            self.stdout.write(
                f"{prefix} post {post.pk}: {width}x{height}"
            )

        action = "would update" if dry_run else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete: {action}={updated}, failed={failed}, "
                f"already_populated={already_populated}."
            )
        )

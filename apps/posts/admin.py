from django.contrib import admin

from .models import PostCategory, Post
from .revalidation import revalidate_post_paths


@admin.register(PostCategory)
class PostCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "club")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "club", "status", "published_at", "is_featured")
    list_filter = ("status", "club", "category", "is_featured")
    search_fields = ("title", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}

    def save_model(self, request, obj, form, change):
        old_slug = None

        if change and obj.pk:
            old_slug = (
                Post.objects.filter(pk=obj.pk)
                .values_list("slug", flat=True)
                .first()
            )

        super().save_model(request, obj, form, change)
        revalidate_post_paths(
            obj,
            reason="Post saved in Django admin",
            old_slug=old_slug,
        )

    def delete_model(self, request, obj):
        post = obj
        super().delete_model(request, obj)
        revalidate_post_paths(post, reason="Post deleted in Django admin")

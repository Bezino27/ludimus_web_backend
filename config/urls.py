from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/public/clubs/", include("apps.clubs.urls")),
    path("api/public/posts/", include("apps.posts.urls")),
    path("api/public/pages/", include("apps.pages.urls")),
    path("api/public/partners/", include("apps.partners.urls")),
    path("api/public/", include("apps.api.urls")),
    path("api/public/teams/", include("apps.teams.urls")),
    path("api/admin/auth/", include("apps.accounts.urls")),
    path("api/admin/posts/", include("apps.posts.admin_urls")),
    path("api/admin/pages/", include("apps.pages.admin_urls")),
    path("api/admin/partners/", include("apps.partners.admin_urls")),
    path("api/admin/polls/", include("apps.polls.admin_urls")),
    path("api/admin/gallery/", include("apps.gallery.admin_urls")),
    path("api/admin/teams/", include("apps.teams.admin_urls")),
    path("api/public/szfb/", include("apps.scraper.urls")),

    path("api/guli/", include("apps.guli.urls")),
    path("api/polls/", include("apps.polls.urls")),
    path("api/public/", include("apps.club_info.urls")),
    

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    

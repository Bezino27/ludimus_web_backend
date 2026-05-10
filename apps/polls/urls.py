from django.urls import path

from . import views

urlpatterns = [
    path("", views.poll_list_create_view, name="poll-list-create"),
    path("latest-result/", views.latest_poll_result_view, name="poll-latest-result"),
    path("<int:poll_id>/", views.poll_detail_view, name="poll-detail"),
    path("<int:poll_id>/vote/", views.poll_vote_view, name="poll-vote"),
    path("<int:poll_id>/results/", views.poll_results_view, name="poll-results"),
]
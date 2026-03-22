from rest_framework.permissions import BasePermission

from apps.clubs.models import ClubMembership


EDITOR_ROLES = {"club_admin", "editor"}
MATCH_ROLES = {"club_admin", "match_manager"}
VIEW_ROLES = {"club_admin", "editor", "match_manager", "viewer"}


def user_has_club_role(user, club, allowed_roles):
    if not user or not user.is_authenticated:
        return False

    return ClubMembership.objects.filter(
        user=user,
        club=club,
        is_active=True,
        role__in=allowed_roles,
    ).exists()


class HasClubEditorAccess(BasePermission):
    def has_object_permission(self, request, view, obj):
        return user_has_club_role(request.user, obj.club, EDITOR_ROLES)

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
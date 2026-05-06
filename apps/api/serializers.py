from rest_framework import serializers

from apps.clubs.serializers import ClubSerializer
from apps.homepage.serializers import HomepageSectionSerializer
from apps.posts.serializers import PostListSerializer
from apps.partners.serializers import PartnerSerializer
from apps.pages.serializers import PageSerializer


class HomePageResponseSerializer(serializers.Serializer):
    club = ClubSerializer()
    sections = HomepageSectionSerializer(many=True)
    latest_posts = PostListSerializer(many=True)
    partners = PartnerSerializer(many=True)
    menu_pages = PageSerializer(many=True)

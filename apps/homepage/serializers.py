from rest_framework import serializers
from .models import HomepageSection


class HomepageSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomepageSection
        fields = [
            "id",
            "title",
            "section_type",
            "is_active",
            "order",
            "config",
        ]
from urllib.parse import urlparse

from django.db import models
from apps.clubs.models import Club


class ContactInfo(models.Model):
    club = models.OneToOneField(
        Club,
        on_delete=models.CASCADE,
        related_name="contact_info",
    )

    address = models.CharField(max_length=255)
    chairman_name = models.CharField(max_length=160, blank=True)

    email = models.EmailField()
    phone = models.CharField(max_length=80)
    iban = models.CharField(max_length=80, blank=True)

    map_label = models.CharField(max_length=160)
    map_address = models.CharField(max_length=255)

    latitude = models.DecimalField(max_digits=18, decimal_places=15)
    longitude = models.DecimalField(max_digits=18, decimal_places=15)

    note = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kontaktné informácie"
        verbose_name_plural = "Kontaktné informácie"

    def __str__(self):
        return f"Kontakt - {self.club.name}"


class ClubDocument(models.Model):
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    title = models.CharField(max_length=180)
    file = models.FileField(upload_to="club_documents/")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Klubový dokument"
        verbose_name_plural = "Klubové dokumenty"
        ordering = ["order", "title"]

    def __str__(self):
        return f"{self.title} - {self.club.name}"


class ClubLink(models.Model):
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="links",
    )
    title = models.CharField(max_length=100)
    url = models.URLField()
    icon_type = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="Ak necháš prázdne, typ ikonky sa automaticky určí podľa URL.",
    )
    logo = models.FileField(upload_to="clubs/links/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = "Klubový odkaz"
        verbose_name_plural = "Klubové odkazy"

    def __str__(self):
        return f"{self.club.name} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.icon_type:
            self.icon_type = self.detect_icon_type(self.url)

        super().save(*args, **kwargs)

    @staticmethod
    def detect_icon_type(url):
        hostname = (urlparse(url).hostname or "").lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        if hostname.endswith("instagram.com"):
            return "instagram"
        if hostname.endswith("facebook.com") or hostname.endswith("fb.com"):
            return "facebook"
        if hostname.endswith("youtube.com") or hostname.endswith("youtu.be"):
            return "youtube"
        if hostname.endswith("tiktok.com"):
            return "tiktok"
        if hostname.endswith("flickr.com"):
            return "flickr"
        if hostname.endswith("szfb.sk") or hostname.endswith("florbalnet.sk"):
            return "szfb"
        if hostname.endswith("florbalexpert.sk") or hostname.endswith("florbalexpert.cz"):
            return "florbal_expert"
        if hostname.endswith("ludimus.sk"):
            return "ludimus"

        return "website"

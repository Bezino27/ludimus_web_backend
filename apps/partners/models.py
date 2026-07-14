from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TimeStampedModel


class PartnerQuerySet(models.QuerySet):
    def ordered_for_public(self):
        """
        Verejné poradie skupín:
        generálny -> hlavný -> partner/bez rozdelenia -> mediálny.

        Partner bez typu sa na verejnom webe správa ako bežný partner.
        """
        tier_rank = models.Case(
            models.When(tier="general", then=models.Value(0)),
            models.When(tier="main", then=models.Value(1)),
            models.When(tier="partner", then=models.Value(2)),
            models.When(tier="", then=models.Value(2)),
            models.When(tier="media", then=models.Value(3)),
            default=models.Value(4),
            output_field=models.IntegerField(),
        )

        return self.annotate(_tier_rank=tier_rank).order_by(
            "_tier_rank",
            "order",
            "name",
            "id",
        )

    def ordered_for_admin(self):
        """
        Admin poradie skupín:
        generálny -> hlavný -> partner -> mediálny -> bez rozdelenia.
        """
        tier_rank = models.Case(
            models.When(tier="general", then=models.Value(0)),
            models.When(tier="main", then=models.Value(1)),
            models.When(tier="partner", then=models.Value(2)),
            models.When(tier="media", then=models.Value(3)),
            models.When(tier="", then=models.Value(4)),
            default=models.Value(5),
            output_field=models.IntegerField(),
        )

        return self.annotate(_tier_rank=tier_rank).order_by(
            "_tier_rank",
            "order",
            "name",
            "id",
        )


class Partner(TimeStampedModel):
    class Tier(models.TextChoices):
        GENERAL = "general", "Generálny partner"
        MAIN = "main", "Hlavný partner"
        PARTNER = "partner", "Partner"
        MEDIA = "media", "Mediálny partner"

    TIER_UNGROUPED = ""
    UNGROUPED_LABEL = "Bez rozdelenia"

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="partners",
    )
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="partners/", blank=True, null=True)
    logo_url = models.URLField(blank=True)
    website = models.URLField(blank=True)
    tier = models.CharField(
        max_length=50,
        choices=Tier.choices,
        blank=True,
        default=TIER_UNGROUPED,
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = PartnerQuerySet.as_manager()

    class Meta:
        ordering = ["order", "name", "id"]
        indexes = [
            models.Index(fields=["club", "tier", "order"]),
            models.Index(fields=["club", "is_active"]),
        ]

    def __str__(self):
        return self.name

    @property
    def tier_label(self):
        if not self.tier:
            return self.UNGROUPED_LABEL
        return self.get_tier_display()

    @property
    def public_tier(self):
        """
        Na verejnom webe sa partner bez typu zobrazí medzi bežnými partnermi.
        """
        return self.tier or self.Tier.PARTNER

    def clean(self):
        super().clean()

        if not self.logo and not self.logo_url:
            raise ValidationError(
                {
                    "logo": (
                        "Nahraj logo alebo vyplň externú URL loga."
                    )
                }
            )
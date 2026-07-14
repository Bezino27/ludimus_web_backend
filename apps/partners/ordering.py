from .models import Partner


def normalize_partner_group(club_id, tier, *, lock=False):
    """
    Prečísluje partnerov v jednej skupine od nuly bez medzier.

    Pri zápisových operáciách sa volá v databázovej transakcii.
    """
    queryset = Partner.objects.filter(
        club_id=club_id,
        tier=tier,
    ).order_by("order", "name", "id")

    if lock:
        queryset = queryset.select_for_update()

    partners = list(queryset)
    changed = []

    for index, partner in enumerate(partners):
        if partner.order != index:
            partner.order = index
            changed.append(partner)

    if changed:
        Partner.objects.bulk_update(changed, ["order"])

    return partners


def get_next_partner_order(club_id, tier, *, lock=False):
    partners = normalize_partner_group(
        club_id,
        tier,
        lock=lock,
    )
    return len(partners)
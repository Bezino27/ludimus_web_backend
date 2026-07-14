from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Partner


def _delete_logo_after_commit(storage, name):
    if not name:
        return

    transaction.on_commit(lambda: storage.delete(name))


@receiver(pre_save, sender=Partner)
def remember_previous_partner_logo(sender, instance, **kwargs):
    instance._previous_logo_name = ""

    if not instance.pk:
        return

    previous = sender.objects.filter(pk=instance.pk).only("logo").first()
    if previous and previous.logo:
        instance._previous_logo_name = previous.logo.name


@receiver(post_save, sender=Partner)
def delete_replaced_partner_logo(sender, instance, **kwargs):
    previous_name = getattr(instance, "_previous_logo_name", "")
    current_name = instance.logo.name if instance.logo else ""

    if previous_name and previous_name != current_name:
        storage = sender._meta.get_field("logo").storage
        _delete_logo_after_commit(storage, previous_name)


@receiver(post_delete, sender=Partner)
def delete_partner_logo(sender, instance, **kwargs):
    if not instance.logo:
        return

    storage = sender._meta.get_field("logo").storage
    _delete_logo_after_commit(storage, instance.logo.name)
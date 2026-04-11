from django.db import models

class RecruitmentForm(models.Model):
    child_full_name = models.CharField(max_length=255)
    birth_year = models.PositiveIntegerField()
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Náborový formulár"
        verbose_name_plural = "Náborové formuláre"

    def __str__(self):
        return f"{self.child_full_name} ({self.birth_year})"
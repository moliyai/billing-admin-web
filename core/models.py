from django.db import models
from django.contrib.auth.models import User


class Pocket(models.Model):
    name = models.CharField(max_length=255)
    requests_count = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_per_request_over_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Company(models.Model):
    name = models.CharField(max_length=255)
    api_url = models.URLField(max_length=500, blank=True, null=True)
    api_username = models.CharField(max_length=255, blank=True, null=True)
    api_password = models.CharField(max_length=255, blank=True, null=True)
    pocket = models.ForeignKey(Pocket, on_delete=models.RESTRICT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="profiles")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company} - {self.user.username}"


class Invoice(models.Model):
    class StatusChoices(models.TextChoices):
        GENERATED = 'GENERATED', 'Generated'
        PAID = 'PAID', 'Paid'
        CANCELED = 'CANCELED', 'Canceled'

    name = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.RESTRICT, related_name="invoices")
    invoice_month = models.DateField()
    total_requests = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.GENERATED
    )
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'invoice_month')

    def __str__(self):
        return self.name

    @property
    def formatted_invoice_month(self):
        if self.invoice_month:
            return self.invoice_month.strftime('%m-%Y')
        return ""

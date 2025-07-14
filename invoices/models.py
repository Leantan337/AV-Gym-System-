from django.db import models
import uuid
from django.utils import timezone
from members.models import Member


class InvoiceTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    content = models.TextField()  # HTML template with variables
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )  # Will be auto-generated on save
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='invoices')
    template = models.ForeignKey(InvoiceTemplate, on_delete=models.PROTECT)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    due_date = models.DateField()
    pdf_path = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['created_at']),
            models.Index(fields=['member', 'status']),
            models.Index(fields=['number']),
        ]

    def save(self, *args, **kwargs):
        if not self.number:
            # Generate invoice number: INV-YYYY-XXXX
            year = timezone.now().year
            last_invoice = (
                Invoice.objects.filter(number__startswith=f'INV-{year}-')
                .order_by('-number')
                .first()
            )
            if last_invoice:
                last_number = int(last_invoice.number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            self.number = f'INV-{year}-{new_number:04d}'

        # Calculate totals
        self.subtotal = sum(item.total for item in self.items.all())
        self.total = self.subtotal + self.tax
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.number} - {self.member.full_name}'


class InvoiceItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

        # Update invoice totals
        self.invoice.save()

    def __str__(self):
        return f'{self.invoice.number} - {self.description}'

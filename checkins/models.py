from django.db import models
import uuid
from members.models import Member


class CheckIn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='checkins')
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['check_in_time']),
            models.Index(fields=['check_out_time']),
            models.Index(fields=['member', 'check_in_time']),
        ]

    def __str__(self):
        return f'{self.member.full_name} - {self.check_in_time}'

from django.db import models
import uuid

class ResumeScan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.JSONField(null=True, blank=True)
    job = models.TextField(null=True, blank=True)
    expected_score = models.DecimalField(
        null=True, blank=True, max_digits=4, decimal_places=2
    )
    outputs = models.JSONField(null=True, blank=True)
    ip =  models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
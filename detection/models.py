from django.db import models
from django.utils import timezone


class DetectionEvent(models.Model):
    SEV = {1:'Low', 2:'Medium', 3:'High', 4:'Critical'}

    device_id         = models.CharField(max_length=100, default='unknown', db_index=True)
    object_name       = models.CharField(max_length=100, db_index=True)
    confidence        = models.FloatField()
    severity          = models.IntegerField(default=1)
    category          = models.CharField(max_length=50, default='unknown')
    source_model      = models.CharField(max_length=50, default='YOLO')
    bbox              = models.TextField(blank=True, default='[]')
    agent_description = models.TextField(blank=True, null=True)
    agent_provider    = models.CharField(max_length=50, blank=True, null=True)
    detected_at       = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-detected_at']
        indexes  = [
            models.Index(fields=['device_id', 'detected_at']),
            models.Index(fields=['severity',  'detected_at']),
        ]

    def __str__(self):
        return f"[{self.detected_at:%H:%M:%S}] {self.object_name} sev={self.severity}"

    @property
    def severity_label(self):
        return self.SEV.get(self.severity, 'Unknown')

    @property
    def confidence_pct(self):
        return f"{self.confidence * 100:.0f}%"


class SessionSummary(models.Model):
    device_id        = models.CharField(max_length=100, db_index=True)
    date             = models.DateField(db_index=True)
    total_detections = models.IntegerField(default=0)
    critical_alerts  = models.IntegerField(default=0)
    risk_score       = models.FloatField(default=0.0)
    top_objects      = models.TextField(default='{}')
    high_risk_hours  = models.TextField(default='[]')
    agent_analyses   = models.IntegerField(default=0)
    notes            = models.TextField(blank=True, default='')
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['device_id', 'date']
        ordering        = ['-date']

    def __str__(self):
        return f"Summary {self.device_id} {self.date} risk={self.risk_score:.1f}"

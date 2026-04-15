from django.core.management.base import BaseCommand
from django.db.models import Count, Q, Sum
from django.utils import timezone
from detection.models import DetectionEvent, SessionSummary
import json
from collections import defaultdict
from datetime import timedelta

class Command(BaseCommand):
    help = 'Generate daily session summaries from detection events'

    def handle(self, *args, **options):
        # Get all unique device_id and date combinations from DetectionEvent
        dates = DetectionEvent.objects.dates('detected_at', 'day')
        devices = DetectionEvent.objects.values_list('device_id', flat=True).distinct()
        
        summaries_created = 0
        
        for device in devices:
            for date in dates:
                # Get events for this device on this date
                events = DetectionEvent.objects.filter(
                    device_id=device,
                    detected_at__date=date
                )
                
                if not events.exists():
                    continue
                
                # Calculate metrics
                total = events.count()
                critical = events.filter(severity=4).count()
                
                # Risk score (weighted by severity)
                sev_counts = events.values('severity').annotate(count=Count('id'))
                risk_score = sum(s['severity'] * s['count'] for s in sev_counts) / total if total > 0 else 0
                
                # Top objects
                top_objects = dict(
                    events.values_list('object_name')
                    .annotate(count=Count('id'))
                    .order_by('-count')[:5]
                )
                
                # High risk hours
                hourly = defaultdict(int)
                for event in events:
                    hourly[event.detected_at.hour] += 1
                
                avg_hourly = sum(hourly.values()) / max(len(hourly), 1)
                high_risk_hours = [h for h, c in hourly.items() if c > avg_hourly * 1.5]
                
                # Count agent analyses
                agent_count = events.exclude(agent_description__isnull=True).count()
                
                # Create or update summary
                summary, created = SessionSummary.objects.update_or_create(
                    device_id=device,
                    date=date,
                    defaults={
                        'total_detections': total,
                        'critical_alerts': critical,
                        'risk_score': round(risk_score, 2),
                        'top_objects': json.dumps(top_objects),
                        'high_risk_hours': json.dumps(high_risk_hours),
                        'agent_analyses': agent_count,
                    }
                )
                
                summaries_created += 1
                action = "Created" if created else "Updated"
                self.stdout.write(f"{action} summary for {device} on {date}")
        
        self.stdout.write(self.style.SUCCESS(f"Generated {summaries_created} session summaries"))
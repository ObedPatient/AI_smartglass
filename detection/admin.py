from django.contrib import admin
from django.utils.html import format_html
from .models import DetectionEvent, SessionSummary


@admin.register(DetectionEvent)
class DetectionEventAdmin(admin.ModelAdmin):
    list_display   = ('detected_at', 'object_name', 'sev_badge', 'confidence_pct',
                      'source_model', 'category', 'device_id', 'has_agent')
    list_filter    = ('severity', 'source_model', 'device_id', 'category')
    search_fields  = ('object_name', 'device_id', 'agent_description')
    ordering       = ('-detected_at',)
    readonly_fields = ('detected_at',)
    date_hierarchy  = 'detected_at'

    def sev_badge(self, obj):
        colors = {1:'#94A3B8', 2:'#FACC15', 3:'#FB923C', 4:'#F87171'}
        c = colors.get(obj.severity, '#888')
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            c, obj.severity_label
        )
    sev_badge.short_description = 'Severity'

    def has_agent(self, obj):
        return bool(obj.agent_description)
    has_agent.boolean = True
    has_agent.short_description = 'Agent'


@admin.register(SessionSummary)
class SessionSummaryAdmin(admin.ModelAdmin):
    list_display  = ('date', 'device_id', 'total_detections', 'critical_alerts',
                     'risk_score', 'agent_analyses', 'updated_at')
    list_filter   = ('device_id',)
    ordering      = ('-date',)

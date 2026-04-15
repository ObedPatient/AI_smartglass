from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='DetectionEvent',
            fields=[
                ('id',                models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('device_id',         models.CharField(db_index=True, default='unknown', max_length=100)),
                ('object_name',       models.CharField(db_index=True, max_length=100)),
                ('confidence',        models.FloatField()),
                ('severity',          models.IntegerField(default=1)),
                ('category',          models.CharField(default='unknown', max_length=50)),
                ('source_model',      models.CharField(default='YOLO', max_length=50)),
                ('bbox',              models.TextField(blank=True, default='[]')),
                ('agent_description', models.TextField(blank=True, null=True)),
                ('agent_provider',    models.CharField(blank=True, max_length=50, null=True)),
                ('detected_at',       models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={'ordering': ['-detected_at']},
        ),
        migrations.CreateModel(
            name='SessionSummary',
            fields=[
                ('id',               models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('device_id',        models.CharField(db_index=True, max_length=100)),
                ('date',             models.DateField(db_index=True)),
                ('total_detections', models.IntegerField(default=0)),
                ('critical_alerts',  models.IntegerField(default=0)),
                ('risk_score',       models.FloatField(default=0.0)),
                ('top_objects',      models.TextField(default='{}')),
                ('high_risk_hours',  models.TextField(default='[]')),
                ('agent_analyses',   models.IntegerField(default=0)),
                ('notes',            models.TextField(blank=True, default='')),
                ('created_at',       models.DateTimeField(auto_now_add=True)),
                ('updated_at',       models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-date'], 'unique_together': {('device_id', 'date')}},
        ),
        migrations.AddIndex(
            model_name='detectionevent',
            index=models.Index(fields=['device_id', 'detected_at'], name='det_dev_time_idx'),
        ),
        migrations.AddIndex(
            model_name='detectionevent',
            index=models.Index(fields=['severity', 'detected_at'], name='det_sev_time_idx'),
        ),
    ]

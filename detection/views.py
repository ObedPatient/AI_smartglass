import json
import queue
import threading
import logging
import re
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import datetime

from .pdf_generator import PDFReportGenerator
from .agent import VisionAgent

logger = logging.getLogger(__name__)
agent = VisionAgent()

# ── SSE broadcast ────────────────────────────────────────────────────
_clients = []
_lock = threading.Lock()
_latest = None

def _broadcast(data):
    global _latest
    _latest = data
    payload = f"data: {json.dumps(data)}\n\n"
    with _lock:
        dead = [q for q in _clients if not _try_put(q, payload)]
        for q in dead:
            _clients.remove(q)

def _try_put(q, payload):
    try:
        q.put_nowait(payload)
        return True
    except queue.Full:
        return False

def _parse_agent_description(desc):
    """Extract obstacle info from AI description for ESP32 audio triggers"""
    if not desc:
        return [], 0, 0
    
    desc_lower = desc.lower()
    detections = []
    
    # Critical hazards (severity 5)
    critical_keywords = {
        'person': 5, 'people': 5, 'knife': 5, 'scissors': 5, 
        'stairs': 4, 'staircase': 4, 'step': 4
    }
    
    # High severity obstacles (severity 3-4)
    high_keywords = {
        'door': 3, 'table': 3, 'dining': 3, 'obstacle': 3,
        'chair': 2, 'sofa': 2, 'couch': 2, 'bed': 2
    }
    
    # Check for critical hazards first
    for keyword, severity in critical_keywords.items():
        if keyword in desc_lower:
            detections.append({
                'object': keyword,
                'confidence': 0.85,
                'severity': severity,
                'source': 'VisionAgent'
            })
    
    # Check for other obstacles
    for keyword, severity in high_keywords.items():
        if keyword in desc_lower:
            detections.append({
                'object': keyword,
                'confidence': 0.75,
                'severity': severity,
                'source': 'VisionAgent'
            })
    
    # Deduplicate and get max severity
    seen = set()
    unique_detections = []
    max_severity = 0
    
    for d in detections:
        if d['object'] not in seen:
            seen.add(d['object'])
            unique_detections.append(d)
            max_severity = max(max_severity, d['severity'])
    
    obstacles_count = len(unique_detections)
    
    return unique_detections[:5], obstacles_count, max_severity

def _save_detection(result, device_id):
    """Save detection event to database"""
    try:
        from .models import DetectionEvent
        if result.get('detections'):
            for det in result['detections']:
                DetectionEvent.objects.create(
                    device_id=device_id,
                    object_name=det['object'],
                    confidence=det['confidence'],
                    severity=det['severity'],
                    category='obstacle',
                    source_model=det.get('source', 'VisionAgent'),
                    agent_description=result.get('agent_description'),
                    agent_provider=result.get('agent_provider'),
                )
    except Exception as e:
        logger.error(f'DB save error: {e}')

# ── Pages ─────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    return render(request, 'dashboard/index.html')

@login_required
def log_page(request):
    return render(request, 'dashboard/log.html')

@login_required
def report_page(request):
    return render(request, 'dashboard/report.html')

# ── Auth ──────────────────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user:
            login(request, user)
            return redirect('/')
        messages.error(request, 'Invalid credentials.')
    return render(request, 'registration/login.html')

def logout_view(request):
    logout(request)
    return redirect('/accounts/login/')

# ── ESP32 Detection Endpoint (Vision Agent Only) ─────────────────────
@csrf_exempt
@require_http_methods(['POST'])
def detect(request):
    import time
    start_time = time.time()
    
    image_bytes = request.body
    if not image_bytes:
        return JsonResponse({'error': 'No image'}, status=400)

    device_id = request.headers.get('X-Device-ID', 'unknown')
    
    # Get AI Vision Agent analysis
    desc, provider = agent.analyze(image_bytes)
    
    # Parse description for obstacle detection
    detections, obstacles_count, max_severity = _parse_agent_description(desc)
    
    # Build result
    result = {
        'success': True,
        'objects_detected': len(detections) > 0,
        'total_objects': len(detections),
        'obstacles_count': obstacles_count,
        'max_severity': max_severity if max_severity > 0 else 1,
        'detections': detections,
        'processing_time_ms': round((time.time() - start_time) * 1000, 1),
        'device_id': device_id,
        'timestamp': timezone.now().isoformat(),
        'agent_description': desc,
        'agent_provider': provider,
        'models_used': ['VisionAgent-Gemini/Mistral'],
    }
    
    # Save to database (async)
    threading.Thread(target=_save_detection, args=(result, device_id), daemon=True).start()
    
    # Broadcast to SSE clients
    _broadcast(result)
    
    return JsonResponse(result)

# ── SSE Stream ────────────────────────────────────────────────────────
def stream(request):
    def gen():
        q = queue.Queue(maxsize=50)
        with _lock:
            _clients.append(q)
        if _latest:
            yield f"data: {json.dumps(_latest)}\n\n"
        try:
            while True:
                try:
                    yield q.get(timeout=25)
                except queue.Empty:
                    yield ': heartbeat\n\n'
        except GeneratorExit:
            pass
        finally:
            with _lock:
                if q in _clients:
                    _clients.remove(q)
    
    r = StreamingHttpResponse(gen(), content_type='text/event-stream')
    r['Cache-Control'] = 'no-cache'
    r['X-Accel-Buffering'] = 'no'
    return r

# ── REST Endpoints ────────────────────────────────────────────────────
def latest(request):
    return JsonResponse(_latest if _latest else {'success': False})

def health(request):
    return JsonResponse({
        'status': 'healthy',
        'model_loaded': True,
        'models': ['VisionAgent'],
        'agent': {
            'gemini': bool(agent.gemini_key),
            'mistral': bool(agent.mistral_key),
        },
        'timestamp': timezone.now().isoformat(),
    })

@login_required
def log_api(request):
    from .models import DetectionEvent
    page = max(1, int(request.GET.get('page', 1)))
    per_page = min(200, int(request.GET.get('per_page', 50)))
    sev = request.GET.get('severity', '')
    src = request.GET.get('source', '')
    search = request.GET.get('search', '')
    device = request.GET.get('device_id', '')

    qs = DetectionEvent.objects.all()
    if sev:
        qs = qs.filter(severity=int(sev))
    if src:
        qs = qs.filter(source_model=src)
    if device:
        qs = qs.filter(device_id=device)
    if search:
        qs = qs.filter(object_name__icontains=search)

    total = qs.count()
    start = (page - 1) * per_page
    events = qs.order_by('-detected_at')[start:start + per_page]

    return JsonResponse({
        'total': total,
        'page': page,
        'per_page': per_page,
        'results': [{
            'id': e.id,
            'time': e.detected_at.strftime('%H:%M:%S'),
            'date': e.detected_at.strftime('%Y-%m-%d'),
            'object': e.object_name,
            'conf': round(e.confidence, 3),
            'severity': e.severity,
            'source': e.source_model,
            'device': e.device_id,
            'agent': e.agent_description or '',
            'provider': e.agent_provider or '',
        } for e in events]
    })

@login_required
def report_api(request):
    from .models import DetectionEvent
    from collections import defaultdict
    from django.db.models import Count, Min, Max
    
    qs = DetectionEvent.objects.all()
    total = qs.count()
    
    if total == 0:
        return JsonResponse({'analysis': {'message': 'No detection events'}, 'recommendations': []})
    
    # Simple analysis without BehaviorAnalyzer
    date_range = qs.aggregate(first=Min('detected_at'), last=Max('detected_at'))
    severity_dist = dict(qs.values('severity').annotate(count=Count('severity')).values_list('severity', 'count'))
    frequent_objects = list(qs.values('object_name').annotate(count=Count('object_name')).order_by('-count')[:10])
    
    analysis = {
        'total_detections': total,
        'unique_objects': qs.values('object_name').distinct().count(),
        'risk_score': round(sum(int(s) * c for s, c in severity_dist.items()) / total, 2),
        'severity_distribution': severity_dist,
        'frequent_objects': [{'object': obj['object_name'], 'count': obj['count']} for obj in frequent_objects],
        'first_detection': date_range['first'].isoformat() if date_range['first'] else None,
        'last_detection': date_range['last'].isoformat() if date_range['last'] else None,
    }
    
    # Simple recommendations
    recs = []
    if analysis['risk_score'] > 3:
        recs.append({'type': 'risk', 'priority': 'high', 'message': 'High risk level detected'})
    
    return JsonResponse({'analysis': analysis, 'recommendations': recs})

@login_required
def download_report_pdf(request):
    """Generate and download PDF report"""
    from .models import DetectionEvent
    from django.db.models import Count, Min, Max
    
    qs = DetectionEvent.objects.all()
    date_range = qs.aggregate(first=Min('detected_at'), last=Max('detected_at'))
    total_detections = qs.count()
    
    severity_dist = {}
    for sev in qs.values('severity').annotate(count=Count('severity')):
        severity_dist[str(sev['severity'])] = sev['count']
    
    frequent_objects = list(
        qs.values('object_name')
        .annotate(count=Count('object_name'))
        .order_by('-count')[:10]
    )
    
    analysis = {
        'total_detections': total_detections,
        'unique_objects': qs.values('object_name').distinct().count(),
        'risk_score': round(sum(int(s) * c for s, c in severity_dist.items()) / max(total_detections, 1), 2),
        'severity_distribution': severity_dist,
        'frequent_objects': [{'object': obj['object_name'], 'count': obj['count']} for obj in frequent_objects],
        'first_detection': date_range['first'].strftime('%Y-%m-%d %H:%M') if date_range['first'] else 'N/A',
        'last_detection': date_range['last'].strftime('%Y-%m-%d %H:%M') if date_range['last'] else 'N/A',
    }
    
    recs = [{'type': 'info', 'priority': 'low', 'message': 'Vision Agent active - monitoring environment'}]
    
    pdf_gen = PDFReportGenerator()
    pdf_buffer = pdf_gen.generate_report(analysis, recs)
    
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="smartglass_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    return response

@login_required
def download_log_pdf(request):
    """Generate and download PDF of filtered detection log"""
    from .models import DetectionEvent
    from .pdf_generator import LogPDFGenerator
    
    sev = request.GET.get('severity', '')
    search = request.GET.get('search', '')
    device = request.GET.get('device_id', '')
    
    qs = DetectionEvent.objects.all()
    filters_applied = {}
    
    if sev:
        qs = qs.filter(severity=int(sev))
        filters_applied['severity'] = sev
    if device:
        qs = qs.filter(device_id=device)
        filters_applied['device_id'] = device
    if search:
        qs = qs.filter(object_name__icontains=search)
        filters_applied['search'] = search
    
    events = qs.order_by('-detected_at')[:1000]
    
    events_data = [{
        'id': e.id,
        'time': e.detected_at.strftime('%H:%M:%S'),
        'date': e.detected_at.strftime('%Y-%m-%d'),
        'object': e.object_name,
        'conf': round(e.confidence, 3),
        'severity': e.severity,
        'source': e.source_model,
        'device': e.device_id,
        'agent': e.agent_description or '',
        'provider': e.agent_provider or '',
    } for e in events]
    
    pdf_gen = LogPDFGenerator()
    pdf_buffer = pdf_gen.generate_log_pdf(events_data, filters_applied)
    
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    filename = f"smartglass_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
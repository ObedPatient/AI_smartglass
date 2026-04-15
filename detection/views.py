import json, queue, threading, logging
from django.http              import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts         import render, redirect
from django.utils             import timezone
from django.contrib.auth      import authenticate, login, logout
from django.contrib           import messages
# Add to your existing views.py imports
from .pdf_generator         import PDFReportGenerator
from django.http            import HttpResponse
from datetime               import datetime

from .utils  import YOLODetector, BehaviorAnalyzer
from .agent  import VisionAgent

logger   = logging.getLogger(__name__)
detector = YOLODetector()
analyzer = BehaviorAnalyzer()
agent    = VisionAgent()

# ── SSE broadcast ────────────────────────────────────────────────────
_clients = []
_lock    = threading.Lock()
_latest  = None

def _broadcast(data):
    global _latest
    _latest  = data
    payload  = f"data: {json.dumps(data)}\n\n"
    with _lock:
        dead = [q for q in _clients if not _try_put(q, payload)]
        for q in dead: _clients.remove(q)

def _try_put(q, payload):
    try: q.put_nowait(payload); return True
    except queue.Full: return False

def _save(result, device_id):
    try:
        from .models import DetectionEvent
        for det in result.get('detections', []):
            DetectionEvent.objects.create(
                device_id=device_id, object_name=det['object'],
                confidence=det['confidence'], severity=det['severity'],
                category=det['category'], source_model=det.get('source','YOLO'),
                bbox=json.dumps(det.get('bbox',[])),
                agent_description=result.get('agent_description'),
                agent_provider=result.get('agent_provider'),
            )
    except Exception as e:
        logger.error('DB save: %s', e)

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
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect('/')
        messages.error(request, 'Invalid credentials.')
    return render(request, 'registration/login.html')

def logout_view(request):
    logout(request)
    return redirect('/accounts/login/')

# ── ESP32 detection endpoint ─────────────────────────────────────────
@csrf_exempt
@require_http_methods(['POST'])
def detect(request):
    image_bytes = request.body
    if not image_bytes:
        return JsonResponse({'error': 'No image'}, status=400)

    device_id = request.headers.get('X-Device-ID', 'unknown')

    # YOLO ensemble
    result = detector.detect(image_bytes)
    if 'error' in result:
        return JsonResponse(result, status=500)

    # AI Vision Agent (every 15s)
    desc, provider = agent.analyze(image_bytes)

    result.update({
        'device_id':         device_id,
        'timestamp':         timezone.now().isoformat(),
        'agent_description': desc,
        'agent_provider':    provider,
    })

    threading.Thread(target=_save, args=(result, device_id), daemon=True).start()
    _broadcast(result)
    return JsonResponse(result)

# ── SSE stream ────────────────────────────────────────────────────────
def stream(request):
    def gen():
        q = queue.Queue(maxsize=50)
        with _lock: _clients.append(q)
        if _latest:
            yield f"data: {json.dumps(_latest)}\n\n"
        try:
            while True:
                try:    yield q.get(timeout=25)
                except queue.Empty: yield ': heartbeat\n\n'
        except GeneratorExit:
            pass
        finally:
            with _lock:
                if q in _clients: _clients.remove(q)
    r = StreamingHttpResponse(gen(), content_type='text/event-stream')
    r['Cache-Control'] = 'no-cache'
    r['X-Accel-Buffering'] = 'no'
    return r

# ── REST endpoints ────────────────────────────────────────────────────
def latest(request):
    return JsonResponse(_latest) if _latest else JsonResponse({'success':False})

def health(request):
    return JsonResponse({
        'status':       'healthy',
        'model_loaded': len(detector.models) > 0,
        'models':       [l for l,_ in detector.models],
        'agent': {
            'gemini':  bool(agent.gemini_key),
            'mistral': bool(agent.mistral_key),
        },
        'timestamp': timezone.now().isoformat(),
    })

@login_required
def log_api(request):
    from .models import DetectionEvent
    page     = max(1, int(request.GET.get('page', 1)))
    per_page = min(200, int(request.GET.get('per_page', 50)))
    sev      = request.GET.get('severity', '')
    src      = request.GET.get('source', '')
    search   = request.GET.get('search', '')
    device   = request.GET.get('device_id', '')

    qs = DetectionEvent.objects.all()
    if sev:    qs = qs.filter(severity=int(sev))
    if src:    qs = qs.filter(source_model=src)
    if device: qs = qs.filter(device_id=device)
    if search: qs = qs.filter(object_name__icontains=search)

    total  = qs.count()
    start  = (page-1)*per_page
    events = qs[start:start+per_page]

    return JsonResponse({
        'total': total, 'page': page, 'per_page': per_page,
        'results': [{
            'id':       e.id,
            'time':     e.detected_at.strftime('%H:%M:%S'),
            'date':     e.detected_at.strftime('%Y-%m-%d'),
            'object':   e.object_name,
            'conf':     round(e.confidence, 3),
            'severity': e.severity,
            'sev_label':e.severity_label,
            'category': e.category,
            'source':   e.source_model,
            'device':   e.device_id,
            'agent':    e.agent_description or '',
            'provider': e.agent_provider or '',
        } for e in events]
    })

@login_required
def report_api(request):
    from .models import DetectionEvent
    
    qs = DetectionEvent.objects.all()
    analysis = analyzer.analyze(qs, days=None)  
    recs = analyzer.recommendations(analysis)
    
    return JsonResponse({'analysis': analysis, 'recommendations': recs})



# Add this new view function
@login_required
def download_report_pdf(request):
    """Generate and download PDF report"""
    from .models import DetectionEvent
    from django.db.models import Count, Q, Min, Max
    
    # Get all detection events
    qs = DetectionEvent.objects.all()
    
    # Get date range
    date_range = qs.aggregate(
        first=Min('detected_at'),
        last=Max('detected_at')
    )
    
    # Calculate analysis data
    total_detections = qs.count()
    
    # Unique objects
    unique_objects = qs.values('object_name').distinct().count()
    
    # Severity distribution
    severity_dist = {}
    for sev in qs.values('severity').annotate(count=Count('severity')):
        severity_dist[str(sev['severity'])] = sev['count']
    
    # Frequent objects
    frequent_objects = list(
        qs.values('object_name')
        .annotate(count=Count('object_name'))
        .order_by('-count')[:10]
    )
    frequent_objects = [
        {'object': obj['object_name'], 'count': obj['count']}
        for obj in frequent_objects
    ]
    
    # Hourly pattern
    hourly_pattern = {}
    for hour in qs.values('detected_at__hour').annotate(count=Count('id')):
        hourly_pattern[str(hour['detected_at__hour'])] = hour['count']
    
    # Calculate risk score
    high_sev_count = qs.filter(severity__gte=3).count()
    risk_score = (high_sev_count / max(total_detections, 1)) * 5
    
    # High risk hours (hours with above average activity)
    avg_hourly = sum(hourly_pattern.values()) / max(len(hourly_pattern), 1)
    high_risk_hours = [
        hour for hour, count in hourly_pattern.items()
        if count > avg_hourly * 1.5
    ]
    
    # Behavior analysis
    analysis = {
        'total_detections': total_detections,
        'unique_objects': unique_objects,
        'risk_score': round(risk_score, 2),
        'high_risk_hours': high_risk_hours,
        'severity_distribution': severity_dist,
        'frequent_objects': frequent_objects,
        'hourly_pattern': hourly_pattern,
        'first_detection': date_range['first'].strftime('%Y-%m-%d %H:%M') if date_range['first'] else 'N/A',
        'last_detection': date_range['last'].strftime('%Y-%m-%d %H:%M') if date_range['last'] else 'N/A',
    }
    
    # Get recommendations from analyzer
    recs = analyzer.recommendations(analysis)
    
    # Generate PDF
    pdf_gen = PDFReportGenerator()
    pdf_buffer = pdf_gen.generate_report(analysis, recs)
    
    # Create HTTP response
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="smartglass_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    return response



@login_required
def download_log_pdf(request):
    """Generate and download PDF of filtered detection log"""
    from .models import DetectionEvent
    from .pdf_generator import LogPDFGenerator
    
    # Get filter parameters (same as log_api)
    sev = request.GET.get('severity', '')
    src = request.GET.get('source', '')
    search = request.GET.get('search', '')
    device = request.GET.get('device_id', '')
    
    # Build queryset with filters
    qs = DetectionEvent.objects.all()
    
    filters_applied = {}
    if sev:
        qs = qs.filter(severity=int(sev))
        filters_applied['severity'] = sev
    if src:
        qs = qs.filter(source_model=src)
        filters_applied['source'] = src
    if device:
        qs = qs.filter(device_id=device)
        filters_applied['device_id'] = device
    if search:
        qs = qs.filter(object_name__icontains=search)
        filters_applied['search'] = search
    
    # Limit to last 1000 records for PDF size
    events = qs.order_by('-detected_at')[:1000]
    
    # Format events for PDF
    events_data = []
    for e in events:
        events_data.append({
            'id': e.id,
            'time': e.detected_at.strftime('%H:%M:%S'),
            'date': e.detected_at.strftime('%Y-%m-%d'),
            'object': e.object_name,
            'conf': round(e.confidence, 3),
            'severity': e.severity,
            'sev_label': e.severity_label,
            'category': e.category,
            'source': e.source_model,
            'device': e.device_id,
            'agent': e.agent_description or '',
            'provider': e.agent_provider or '',
        })
    
    # Generate PDF
    pdf_gen = LogPDFGenerator()
    pdf_buffer = pdf_gen.generate_log_pdf(events_data, filters_applied)
    
    # Create HTTP response
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    
    # Create filename with filters
    filename_parts = ['smartglass_log']
    if filters_applied.get('severity'):
        filename_parts.append(f"sev{filters_applied['severity']}")
    if filters_applied.get('search'):
        filename_parts.append(f"search_{filters_applied['search'][:10]}")
    filename_parts.append(datetime.now().strftime("%Y%m%d_%H%M%S"))
    
    filename = '_'.join(filename_parts) + '.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
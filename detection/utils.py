import cv2
import numpy as np
from ultralytics import YOLO
from django.conf import settings
import os, time, logging
from collections import defaultdict

logger = logging.getLogger(__name__)

ALL_CLASSES = {
    # ── Indoor custom model (10 classes) ───────────────────────────
    'TV':           {'severity':2,'category':'electronics','alert':True},
    'bed':          {'severity':2,'category':'furniture',  'alert':True},
    'chair':        {'severity':2,'category':'furniture',  'alert':True},
    'clock':        {'severity':1,'category':'object',     'alert':False},
    'consoleeeeee': {'severity':2,'category':'furniture',  'alert':True},
    'door':         {'severity':3,'category':'structural', 'alert':True},
    'fan':          {'severity':2,'category':'appliance',  'alert':True},
    'light':        {'severity':1,'category':'fixture',    'alert':False},
    'sofa':         {'severity':2,'category':'furniture',  'alert':True},
    'table':        {'severity':3,'category':'furniture',  'alert':True},
    # ── 80 COCO classes ────────────────────────────────────────────
    'person':        {'severity':4,'category':'living',    'alert':True},
    'bicycle':       {'severity':3,'category':'vehicle',   'alert':True},
    'car':           {'severity':3,'category':'vehicle',   'alert':True},
    'motorcycle':    {'severity':3,'category':'vehicle',   'alert':True},
    'airplane':      {'severity':1,'category':'vehicle',   'alert':False},
    'bus':           {'severity':3,'category':'vehicle',   'alert':True},
    'train':         {'severity':3,'category':'vehicle',   'alert':True},
    'truck':         {'severity':3,'category':'vehicle',   'alert':True},
    'boat':          {'severity':2,'category':'vehicle',   'alert':True},
    'traffic light': {'severity':1,'category':'traffic',   'alert':False},
    'fire hydrant':  {'severity':2,'category':'traffic',   'alert':True},
    'stop sign':     {'severity':1,'category':'traffic',   'alert':False},
    'parking meter': {'severity':2,'category':'traffic',   'alert':True},
    'bench':         {'severity':2,'category':'furniture', 'alert':True},
    'bird':          {'severity':1,'category':'animal',    'alert':False},
    'cat':           {'severity':2,'category':'pet',       'alert':True},
    'dog':           {'severity':3,'category':'pet',       'alert':True},
    'horse':         {'severity':3,'category':'animal',    'alert':True},
    'sheep':         {'severity':2,'category':'animal',    'alert':True},
    'cow':           {'severity':3,'category':'animal',    'alert':True},
    'elephant':      {'severity':4,'category':'animal',    'alert':True},
    'bear':          {'severity':4,'category':'animal',    'alert':True},
    'zebra':         {'severity':3,'category':'animal',    'alert':True},
    'giraffe':       {'severity':3,'category':'animal',    'alert':True},
    'backpack':      {'severity':2,'category':'bag',       'alert':True},
    'umbrella':      {'severity':2,'category':'object',    'alert':True},
    'handbag':       {'severity':1,'category':'bag',       'alert':True},
    'tie':           {'severity':1,'category':'clothing',  'alert':False},
    'suitcase':      {'severity':3,'category':'bag',       'alert':True},
    'frisbee':       {'severity':1,'category':'sports',    'alert':False},
    'skis':          {'severity':3,'category':'sports',    'alert':True},
    'snowboard':     {'severity':3,'category':'sports',    'alert':True},
    'sports ball':   {'severity':2,'category':'sports',    'alert':True},
    'kite':          {'severity':1,'category':'sports',    'alert':False},
    'baseball bat':  {'severity':3,'category':'sports',    'alert':True},
    'baseball glove':{'severity':1,'category':'sports',    'alert':False},
    'skateboard':    {'severity':3,'category':'sports',    'alert':True},
    'surfboard':     {'severity':3,'category':'sports',    'alert':True},
    'tennis racket': {'severity':2,'category':'sports',    'alert':True},
    'bottle':        {'severity':2,'category':'kitchen',   'alert':True},
    'wine glass':    {'severity':3,'category':'kitchen',   'alert':True},
    'cup':           {'severity':2,'category':'kitchen',   'alert':True},
    'fork':          {'severity':2,'category':'utensil',   'alert':True},
    'knife':         {'severity':4,'category':'utensil',   'alert':True},
    'spoon':         {'severity':1,'category':'utensil',   'alert':False},
    'bowl':          {'severity':2,'category':'kitchen',   'alert':True},
    'banana':        {'severity':1,'category':'food',      'alert':False},
    'apple':         {'severity':1,'category':'food',      'alert':False},
    'sandwich':      {'severity':1,'category':'food',      'alert':False},
    'orange':        {'severity':1,'category':'food',      'alert':False},
    'broccoli':      {'severity':1,'category':'food',      'alert':False},
    'carrot':        {'severity':1,'category':'food',      'alert':False},
    'hot dog':       {'severity':1,'category':'food',      'alert':False},
    'pizza':         {'severity':1,'category':'food',      'alert':False},
    'donut':         {'severity':1,'category':'food',      'alert':False},
    'cake':          {'severity':1,'category':'food',      'alert':False},
    'couch':         {'severity':2,'category':'furniture', 'alert':True},
    'potted plant':  {'severity':1,'category':'decoration','alert':True},
    'dining table':  {'severity':3,'category':'furniture', 'alert':True},
    'toilet':        {'severity':2,'category':'fixture',   'alert':True},
    'tv':            {'severity':1,'category':'electronics','alert':True},
    'laptop':        {'severity':2,'category':'electronics','alert':True},
    'mouse':         {'severity':1,'category':'electronics','alert':False},
    'remote':        {'severity':1,'category':'electronics','alert':False},
    'keyboard':      {'severity':1,'category':'electronics','alert':False},
    'cell phone':    {'severity':1,'category':'electronics','alert':False},
    'microwave':     {'severity':2,'category':'appliance', 'alert':True},
    'oven':          {'severity':3,'category':'appliance', 'alert':True},
    'toaster':       {'severity':2,'category':'appliance', 'alert':True},
    'sink':          {'severity':2,'category':'fixture',   'alert':True},
    'refrigerator':  {'severity':2,'category':'appliance', 'alert':True},
    'book':          {'severity':1,'category':'object',    'alert':False},
    'vase':          {'severity':2,'category':'decoration','alert':True},
    'scissors':      {'severity':3,'category':'tool',      'alert':True},
    'teddy bear':    {'severity':1,'category':'toy',       'alert':False},
    'hair drier':    {'severity':2,'category':'appliance', 'alert':True},
    'toothbrush':    {'severity':1,'category':'personal',  'alert':False},
}

def get_info(name):
    return ALL_CLASSES.get(name) or ALL_CLASSES.get(name.lower()) or \
           {'severity':1,'category':'unknown','alert':False}

def iou(a, b):
    xA,yA = max(a[0],b[0]), max(a[1],b[1])
    xB,yB = min(a[2],b[2]), min(a[3],b[3])
    inter = max(0,xB-xA)*max(0,yB-yA)
    if not inter: return 0.0
    return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)

def ensemble_nms(dets, thresh=0.45):
    if not dets: return []
    by_cls = defaultdict(list)
    for d in dets: by_cls[d['object'].lower()].append(d)
    out = []
    for _, cls_dets in by_cls.items():
        cls_dets = sorted(cls_dets, key=lambda x: x['confidence'], reverse=True)
        while cls_dets:
            best = cls_dets.pop(0); out.append(best)
            cls_dets = [d for d in cls_dets if iou(best['bbox'],d['bbox']) < thresh]
    return sorted(out, key=lambda x: x['confidence'], reverse=True)

def run_model(model, img, conf, label):
    out = []
    try:
        res = model(img, conf=conf, verbose=False)
        if not res or res[0].boxes is None: return out
        for box in res[0].boxes:
            x1,y1,x2,y2 = [float(v) for v in box.xyxy[0].tolist()]
            name = model.names[int(box.cls[0])]
            info = get_info(name)
            out.append({
                'object':     name,
                'confidence': round(float(box.conf[0]),4),
                'severity':   info['severity'],
                'category':   info['category'],
                'alert':      info['alert'],
                'bbox':       [x1,y1,x2,y2],
                'center':     [round((x1+x2)/2,1), round((y1+y2)/2,1)],
                'width':      round(x2-x1,1),
                'height':     round(y2-y1,1),
                'source':     label,
            })
    except Exception as e:
        logger.error('[%s] error: %s', label, e)
    return out


class YOLODetector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ready = False
        return cls._instance

    def __init__(self):
        if self._ready: return
        self._ready  = True
        self.models  = []
        self._init()

    def _init(self):
        d = str(getattr(settings,'YOLO_MODELS_DIR','yolo_models'))
        os.makedirs(d, exist_ok=True)
        self._load('yolov8n', d, required=True)
        if getattr(settings,'ENABLE_YOLOV8S',True):
            self._load('yolov8s', d, required=False)
        if getattr(settings,'ENABLE_YOLOV8M',False):
            self._load('yolov8m', d, required=False)
        cp = str(getattr(settings,'CUSTOM_MODEL_PATH', os.path.join(d,'indoor_custom.pt')))
        if os.path.exists(cp):
            try:
                m = YOLO(cp)
                self.models.append(('IndoorCustom', m))
                logger.info('✅ IndoorCustom loaded — classes: %s', list(m.names.values()))
            except Exception as e:
                logger.warning('IndoorCustom failed: %s', e)
        else:
            logger.info('ℹ️  No indoor_custom.pt — train on Colab and copy best.pt to yolo_models/')
        if not self.models: raise RuntimeError('No YOLO models loaded.')
        logger.info('✅ Ensemble: %s', [l for l,_ in self.models])

    def _load(self, name, d, required):
        p = os.path.join(d, name+'.pt')
        try:
            m = YOLO(p) if os.path.exists(p) else YOLO(name+'.pt')
            if not os.path.exists(p): m.save(p)
            self.models.append((name.upper(), m))
            logger.info('✅ %s ready', name.upper())
        except Exception as e:
            if required: raise RuntimeError(f'{name} failed: {e}')
            logger.warning('⚠️  %s skipped: %s', name, e)

    def detect(self, image_bytes, conf=None):
        if conf is None: conf = getattr(settings,'CONFIDENCE_THRESHOLD',0.40)
        try:
            img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
            if img is None: return {'error':'Cannot decode image'}
            h, w = img.shape[:2]
            t0   = time.time()
            raw  = []
            for label, model in self.models:
                raw.extend(run_model(model, img, conf, label))
            thresh  = getattr(settings,'NMS_IOU_THRESHOLD',0.45)
            merged  = ensemble_nms(raw, thresh)
            elapsed = (time.time()-t0)*1000
            obs = sum(1 for d in merged if d['alert'] or d['severity']>=2)
            ms  = max((d['severity'] for d in merged), default=1)
            logger.info('Ensemble: %d raw→%d merged | %d obs | sev=%d | %.0fms',
                        len(raw),len(merged),obs,ms,elapsed)
            return {
                'success':True,'objects_detected':len(merged)>0,
                'total_objects':len(merged),'obstacles_count':obs,
                'max_severity':ms,'detections':merged,
                'processing_time_ms':round(elapsed,1),
                'models_used':[l for l,_ in self.models],
                'raw_count':len(raw),'image_info':{'width':w,'height':h},
            }
        except Exception as e:
            logger.error('detect error: %s', e, exc_info=True)
            return {'error':str(e)}


class BehaviorAnalyzer:
    def analyze(self, qs, days=None):  
        """
        Analyze detection events.
        If days is None, analyze ALL events.
        If days is specified, analyze only last N days.
        """
        from django.utils import timezone
        from datetime import timedelta
        from collections import defaultdict
        
        if hasattr(qs, 'filter'): 
            if days is not None:
                cutoff = timezone.now() - timedelta(days=days)
                qs = qs.filter(detected_at__gte=cutoff)
            events = list(qs)
        else:  
            events = qs
            if days is not None:
                cutoff = timezone.now() - timedelta(days=days)
                events = [d for d in events if d.detected_at >= cutoff]
        
        if not events:
            return {'message': f'No detection events found{" in last "+str(days)+" days" if days else ""}'}
        
        obj_c = defaultdict(int)
        sev_c = defaultdict(int)
        hr_c = defaultdict(int)
        
        for d in events:
            obj_c[d.object_name] += 1
            sev_c[d.severity] += 1
            hr_c[d.detected_at.hour] += 1
        
        total = len(events)
        risk = sum(s * c for s, c in sev_c.items()) / total if total else 0
        avg_h = sum(hr_c.values()) / max(len(hr_c), 1)
        
        # Get date range
        dates = [e.detected_at for e in events]
        
        return {
            'total_detections': total,
            'unique_objects': len(obj_c),
            'frequent_objects': [
                {'object': o, 'count': c}
                for o, c in sorted(obj_c.items(), key=lambda x: x[1], reverse=True)[:10]
            ],
            'severity_distribution': dict(sev_c),
            'risk_score': round(risk, 2),
            'high_risk_hours': [h for h, c in hr_c.items() if c > avg_h * 1.5],
            'hourly_pattern': dict(hr_c),
            'first_detection': min(dates).isoformat() if dates else None,
            'last_detection': max(dates).isoformat() if dates else None,
        }
    
    def recommendations(self, analysis):
        recs = []
        
        # Skip if no data
        if analysis.get('message'):
            return recs
        
        # Risk-based recommendations
        risk_score = analysis.get('risk_score', 0)
        if risk_score > 3:
            recs.append({
                'type': 'risk',
                'priority': 'high',
                'message': 'Critical risk level detected — immediate home safety assessment recommended.'
            })
        elif risk_score > 2:
            recs.append({
                'type': 'risk',
                'priority': 'medium',
                'message': 'Moderate risk level — consider reviewing home layout and removing obstacles.'
            })
        
        # Frequent obstacles
        for obj in analysis.get('frequent_objects', [])[:3]:
            if obj['count'] > 50:
                recs.append({
                    'type': 'layout',
                    'priority': 'medium',
                    'message': f"{obj['object']} detected {obj['count']} times — consider relocating it to a safer area."
                })
            elif obj['count'] > 20:
                recs.append({
                    'type': 'layout',
                    'priority': 'low',
                    'message': f"{obj['object']} detected {obj['count']} times — monitor this area."
                })
        
        # High risk hours
        hrs = analysis.get('high_risk_hours', [])
        if hrs:
            hr_str = ', '.join(f"{h}:00" for h in sorted(hrs)[:3])
            recs.append({
                'type': 'timing',
                'priority': 'medium',
                'message': f"High activity detected at {hr_str} — ensure adequate lighting and clear pathways during these hours."
            })
        
        return recs
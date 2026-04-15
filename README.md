# SmartGlass — AI Navigation Dashboard

Full Django project for the ESP32-CAM smart glass system.

## Features
- Real-time obstacle detection dashboard (live SSE stream)
- YOLO ensemble: yolov8n + yolov8s + indoor_custom.pt
- Free AI Vision Agent: Gemini → Mistral → Ollama fallback
- Detection log with search, filter, and CSV export
- Behavior analysis reports for caregivers
- Login/logout authentication
- Django admin panel

## Project Structure
```
smartglass/
├── manage.py
├── requirements.txt
├── .env.example
├── smart_glass/          Django config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── detection/            Main app
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── utils.py          YOLO ensemble
│   ├── agent.py          Free AI vision agents
│   ├── admin.py
│   ├── apps.py
│   └── migrations/
├── templates/
│   ├── dashboard/
│   │   ├── base.html
│   │   ├── index.html    Live dashboard
│   │   ├── log.html      Detection log
│   │   └── report.html   Behavior report
│   └── registration/
│       └── login.html
├── static/
└── yolo_models/          Place .pt files here
```

## Quick Start

```bash
# 1. Enter the project
cd smartglass

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env   # add your free API keys

# 5. Run migrations
python manage.py migrate

# 6. Create admin user
python manage.py createsuperuser

# 7. Start server
python manage.py runserver 0.0.0.0:5000

# 8. Open dashboard
# http://192.168.1.72:5000/
```

## Free API Keys (no credit card)
- Gemini:  https://aistudio.google.com/app/apikey
- Mistral: https://console.mistral.ai

## ESP32 Settings (already correct in your CameraServer.ino)
```cpp
const char* serverUrl = "http://192.168.1.72:5000/api/detect/";
const char* healthUrl = "http://192.168.1.72:5000/api/health/";
```

## YOLO Models
- yolov8n.pt and yolov8s.pt auto-download on first run
- Place your trained indoor_custom.pt in yolo_models/

## API Endpoints
| URL | Method | Description |
|-----|--------|-------------|
| / | GET | Live dashboard |
| /log/ | GET | Detection log page |
| /report/ | GET | Behavior report page |
| /api/detect/ | POST | ESP32 posts JPEG here |
| /api/stream/ | GET | SSE live stream |
| /api/detect/latest/ | GET | Latest result |
| /api/health/ | GET | Health check |
| /api/log/ | GET | Log JSON API |
| /api/report/ | GET | Report JSON API |
| /admin/ | GET | Django admin |

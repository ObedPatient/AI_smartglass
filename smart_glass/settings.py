import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url  

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY   = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-change-in-production')
DEBUG        = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'detection',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'smart_glass.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'smart_glass.wsgi.application'

# ─── DATABASE CONFIGURATION (UPDATED) ─────────────────────────────────
# Automatically uses DATABASE_URL from environment if available (Render)
# Falls back to SQLite for local development

if os.environ.get('DATABASE_URL'):
    # Production: Use PostgreSQL on Render
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=True  # Required for Render PostgreSQL
        )
    }
else:
    # Local development: Use SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Africa/Kigali'
USE_I18N      = True
USE_TZ        = True

# ─── STATIC FILES CONFIGURATION (UPDATED) ─────────────────────────────
STATIC_URL       = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Whitenoise configuration for production static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL        = '/media/'
MEDIA_ROOT       = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL          = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ── CORS ──────────────────────────────────────────────────────────────
# In production, you should restrict this to your actual domains
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [
        'https://ai-smartglass.onrender.com',
        'https://*.onrender.com',
    ]

# ── YOLO ENSEMBLE ─────────────────────────────────────────────────────
YOLO_MODELS_DIR      = BASE_DIR / 'yolo_models'
YOLO_MODEL_PATH      = YOLO_MODELS_DIR / 'yolov8n.pt'
CUSTOM_MODEL_PATH    = YOLO_MODELS_DIR / 'indoor_custom.pt'
ENABLE_YOLOV8S       = True
ENABLE_YOLOV8M       = False   # enable if your machine has enough RAM
CONFIDENCE_THRESHOLD = 0.40
NMS_IOU_THRESHOLD    = 0.45

# ── FREE AI VISION AGENTS ─────────────────────────────────────────────
# Gemini 1.5 Flash — 1,500 req/day free (no credit card)
# Get key: https://aistudio.google.com/app/apikey
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Mistral Pixtral — unlimited requests, 2 RPM free (no credit card)
# Get key: https://console.mistral.ai
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY', '')

# How often the AI agent runs — 15s stays well within free tier limits
AGENT_INTERVAL_SECONDS = 15

# ── SECURITY SETTINGS FOR PRODUCTION ─────────────────────────────────
if not DEBUG:
    # HTTPS settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # HSTS settings
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ── LOGGING ───────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'smart': {
            'format':  '[{levelname}] {asctime} {module}: {message}',
            'style':   '{',
            'datefmt': '%H:%M:%S',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'smart'},
    },
    'loggers': {
        'detection': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'django':    {'handlers': ['console'], 'level': 'WARNING'},
    },
}
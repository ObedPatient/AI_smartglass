from django.urls import path
from . import views

urlpatterns = [
    # ── Pages ────────────────────────────────────────────────────────
    path('',              views.dashboard,    name='dashboard'),
    path('log/',          views.log_page,     name='log_page'),
    path('report/',       views.report_page,  name='report_page'),

    # ── Auth ─────────────────────────────────────────────────────────
    path('accounts/login/',  views.login_view,  name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),

    # ── ESP32 endpoint ───────────────────────────────────────────────
    path('api/detect/',          views.detect,     name='detect'),

    # ── Dashboard live stream ────────────────────────────────────────
    path('api/stream/',          views.stream,     name='stream'),
    path('api/detect/latest/',   views.latest,     name='latest'),

    # ── REST ─────────────────────────────────────────────────────────
    path('api/health/',          views.health,     name='health'),
    path('api/log/',             views.log_api,    name='log_api'),
    path('api/report/',          views.report_api, name='report_api'),
    # Add to your urlpatterns
    path('api/report/pdf/', views.download_report_pdf, name='download_report_pdf'),
    path('api/log/pdf/', views.download_log_pdf, name='download_log_pdf'),
]

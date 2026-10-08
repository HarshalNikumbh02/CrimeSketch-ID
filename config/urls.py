from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from dashboard.views import dashboard_index, settings_view, help_view, about_view
from accounts.views import login_view, logout_view, profile_view
from recognition.views import sketch_search_view, live_camera_view, api_sketch_search, api_webcam_analyze
from searches.views import history_list_view, result_detail_view

urlpatterns = [
    # Core Home & Dashboard
    path('', dashboard_index, name='home'),
    path('dashboard/', include('dashboard.urls')),
    
    
    # Direct Root Feature URLs as per specification
    path('sketch-search/', sketch_search_view, name='sketch_search'),
    path('live-camera/', live_camera_view, name='live_camera'),
    path('history/', history_list_view, name='history'),
    path('results/<str:search_id>/', result_detail_view, name='result_detail'),
    
    # Accounts & Auth
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('settings/', settings_view, name='settings'),
    path('help/', help_view, name='help'),
    path('about/', about_view, name='about'),
    path('accounts/', include('accounts.urls')),
    
    # Feature Modules
    path('candidates/', include('candidates.urls')),
    path('searches/', include('searches.urls')),
    path('recognition/', include('recognition.urls')),
    path('analytics/', include('analytics.urls')),
    path('evaluation/', include('evaluation.urls')),
    
    # API endpoints
    path('api/sketch-search/', api_sketch_search, name='api_sketch_search'),
    path('api/webcam-analyze/', api_webcam_analyze, name='api_webcam_analyze'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

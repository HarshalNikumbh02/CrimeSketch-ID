from django.urls import path
from recognition import views

app_name = 'recognition'

urlpatterns = [
    path('sketch-search/', views.sketch_search_view, name='sketch_search'),
    path('live-camera/', views.live_camera_view, name='live_camera'),
    path('api/sketch-search/', views.api_sketch_search, name='api_sketch_search'),
    path('api/webcam-analyze/', views.api_webcam_analyze, name='api_webcam_analyze'),
]

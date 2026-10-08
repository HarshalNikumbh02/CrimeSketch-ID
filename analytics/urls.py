from django.urls import path
from analytics import views

app_name = 'analytics'

urlpatterns = [
    path('analytics/', views.analytics_view, name='index'),
    path('api/analytics-data/', views.api_analytics_data, name='api_data'),
]

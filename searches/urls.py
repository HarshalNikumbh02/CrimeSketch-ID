from django.urls import path
from searches import views

app_name = 'searches'

urlpatterns = [
    path('history/', views.history_list_view, name='history'),
    path('results/<str:search_id>/', views.result_detail_view, name='detail'),
    path('history/<str:search_id>/delete/', views.history_delete_view, name='delete'),
    path('history/export/csv/', views.export_history_csv, name='export_csv'),
]

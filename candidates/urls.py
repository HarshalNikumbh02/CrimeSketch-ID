from django.urls import path
from candidates import views

app_name = 'candidates'

urlpatterns = [
    path('', views.candidate_list_view, name='list'),
    path('add/', views.candidate_add_view, name='add'),
    path('<str:candidate_id>/', views.candidate_detail_view, name='detail'),
    path('<str:candidate_id>/edit/', views.candidate_edit_view, name='edit'),
    path('<str:candidate_id>/delete/', views.candidate_delete_view, name='delete'),
]

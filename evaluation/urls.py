from django.urls import path
from evaluation import views

app_name = 'evaluation'

urlpatterns = [
    path('evaluation/', views.evaluation_index, name='index'),
    path('evaluation/run/', views.run_evaluation_action, name='run'),
    path('evaluation/setup-benchmark/', views.setup_benchmark_action, name='setup_benchmark'),
]

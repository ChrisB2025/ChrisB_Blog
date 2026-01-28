"""
Imagen URL configuration.
"""

from django.urls import path

from . import views

app_name = 'imagen'

urlpatterns = [
    path('', views.generator_ui, name='generator'),
    path('generate/cover/<int:post_pk>/', views.generate_cover, name='generate_cover'),
    path('generate/custom/', views.generate_custom, name='generate_custom'),
    path('task/<str:task_id>/', views.check_task, name='check_task'),
]

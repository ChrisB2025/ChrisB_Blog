"""
Editor URL configuration.
"""

from django.urls import path

from . import views

app_name = 'editor'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('post/new/', views.post_create, name='post_create'),
    path('post/<int:pk>/', views.post_edit, name='post_edit'),
    path('post/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('post/preview/', views.post_preview, name='post_preview'),
    path('images/', views.image_manager, name='image_manager'),
    path('images/<int:pk>/delete/', views.image_delete, name='image_delete'),
    path('images/select/<int:post_pk>/', views.image_select, name='image_select'),
]

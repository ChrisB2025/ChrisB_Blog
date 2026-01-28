"""
Blog URL configuration.
"""

from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('tags/', views.tag_list, name='tag_list'),
    path('tag/<slug:slug>/', views.tag_detail, name='tag_detail'),
    path('search/', views.search, name='search'),
    path('api/copy-link/', views.copy_link, name='copy_link'),
    path('<slug:slug>/', views.post_detail, name='post_detail'),
]

"""
URL configuration for youtube_claude_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from claude_app.views import transcript_view,index,chatbot_response,youtube_custom_login_view,youtube_dashboard_view,chat_list_view, edit_chat_view, delete_chat_view,youtube_logout


urlpatterns = [
    path('admin/', admin.site.urls),
    path('get-transcript', transcript_view, name='youtube_transcript'),
    path('chat/<int:transcript_id>/', index, name='index'),
    path('get_response/<int:transcript_id>/', chatbot_response, name='chatbot_response'),
    path('get_response/<int:transcript_id>/', chatbot_response, name='chatbot_response'),
    path("logout/",youtube_logout, name="youtube_logout"),
    path("", youtube_custom_login_view, name="youtube_admin_login"),
    path("dashboard/", youtube_dashboard_view, name="youtube_dashboard"),
    path('chats/<int:transcript_id>/', chat_list_view, name='chat_list'),
    path('chats/edit/<int:chat_id>/', edit_chat_view, name='edit_chat'),
    path('chats/delete/<int:chat_id>/', delete_chat_view, name='delete_chat'),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
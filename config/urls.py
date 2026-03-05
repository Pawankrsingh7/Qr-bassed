from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.core.auth_urls')),
    path('', include('apps.core.urls')),
    path('tables/', include('apps.tables.web_urls')),
    path('kitchen/', include('apps.kitchen.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('api/', include('config.api_urls')),
]

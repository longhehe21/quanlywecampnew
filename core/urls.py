from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('inventory.urls')),   # Toàn bộ hệ thống chạy ở đường dẫn gốc
]
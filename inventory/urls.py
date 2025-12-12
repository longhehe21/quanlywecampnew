from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('xoa-hang-hoa/<int:pk>/', views.xoa_hang_hoa, name='xoa_hang_hoa'),
    path('xoa-chi-tiet/<int:pk>/', views.xoa_chi_tiet, name='xoa_chi_tiet'),
]
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # redirect to /admin/
    path('costs/', views.recipe_costs, name='recipe_costs'),
]

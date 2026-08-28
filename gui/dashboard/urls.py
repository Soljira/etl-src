from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("observations/", views.observations, name="observations"),
    path("pipeline/", views.pipeline, name="pipeline"),
]

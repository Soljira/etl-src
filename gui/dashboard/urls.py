from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("observations/", views.observations, name="observations"),
    path("pipeline/", views.pipeline, name="pipeline"),
    path("pipeline/run/", views.pipeline_run, name="pipeline_run"),
    path("pipeline/logs/", views.pipeline_logs, name="pipeline_logs"),
]

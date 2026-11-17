from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("observations/", views.observations, name="observations"),
    path("pipeline/", views.pipeline, name="pipeline"),
    path("pipeline/run/", views.pipeline_run, name="pipeline_run"),
    path("pipeline/logs/", views.pipeline_logs, name="pipeline_logs"),
    path("api-docs/", views.api_docs, name="api_docs"),
    # File download endpoints (raw + processed, served directly by Django)
    path("download/<str:kind>/", views.files_list, name="files_list"),
    path("download/<str:kind>/zip/", views.files_zip, name="files_zip"),
    path("download/<str:kind>/file/<path:filepath>", views.files_single, name="files_single"),
]

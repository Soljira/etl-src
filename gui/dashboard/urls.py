from django.urls import path
from . import views, api_views

urlpatterns = [
    # ── GUI pages ──────────────────────────────────────────────────────────
    path("", views.index, name="index"),
    path("observations/", views.observations, name="observations"),
    path("pipeline/", views.pipeline, name="pipeline"),
    path("pipeline/run/", views.pipeline_run, name="pipeline_run"),
    path("pipeline/logs/", views.pipeline_logs, name="pipeline_logs"),
    path("api-docs/", views.api_docs, name="api_docs"),

    # ── File download pages (GUI, same host) ───────────────────────────────
    path("download/<str:kind>/", views.files_list, name="files_list"),
    path("download/<str:kind>/zip/", views.files_zip, name="files_zip"),
    path("download/<str:kind>/file/<path:filepath>", views.files_single, name="files_single"),

    # ── REST API v1 (served by Django — no Flask server needed) ───────────
    path("api/v1",                                     api_views.api_index,           name="api_index"),
    path("api/v1/",                                    api_views.api_index,           name="api_index_slash"),
    path("api/v1/health",                              api_views.health,              name="api_health"),
    path("api/v1/datasets",                            api_views.list_datasets,       name="api_datasets"),
    path("api/v1/datasets/<str:dataset_id>",           api_views.get_dataset,         name="api_dataset_detail"),
    path("api/v1/categories",                          api_views.list_categories,     name="api_categories"),
    path("api/v1/observations",                        api_views.query_observations,  name="api_observations"),
    path("api/v1/files/<str:kind>",                    api_views.api_files_list,      name="api_files_list"),
    path("api/v1/download/<str:kind>.zip",             api_views.api_download_zip,    name="api_download_zip"),
    path("api/v1/download/<str:kind>/<path:filepath>", api_views.api_download_file,   name="api_download_file"),
]

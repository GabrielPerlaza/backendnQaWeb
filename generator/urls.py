from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("api/dashboard/metrics/", views.dashboard_metrics_api, name="dashboard_metrics_api"),
    path("api/dashboard/charts/", views.dashboard_charts_api, name="dashboard_charts_api"),
    path("chat/", views.chat_view, name="chat"),
    path("chat/<int:chat_id>/", views.chat_view, name="chat"),
    path("generated-cases/", views.generated_cases_view, name="generated_cases"),
    path("project/<int:project_id>/cases/", views.project_test_cases_view, name="project_test_cases"),

    path("projects/", views.projects_view, name="projects"),
    path("history/", views.history_view, name="history"),
    path("metrics/", views.metrics_view, name="metrics"),
    path("profile/", views.profile_view, name="profile"),
    path("upload-project/", views.upload_project_view, name="upload_project"),
    path("project-test-cases/", views.upload_project_view, name="project_test_cases"),  # o view distinta
    path("password-change/", auth_views.PasswordChangeView.as_view( template_name="password_change.html"), name="password_change"),
    path("chat/<int:chat_id>/stream/", views.chat_stream_view, name="chat_stream"),
    path("chat/<int:chat_id>/upload/", views.upload_attachment_view, name="upload_attachment"),
    path("projects/<int:project_id>/download/",views.download_project_test_cases,name="download_project_test_cases"),

    path("projects/delete/<int:project_id>/",views.delete_project,name="delete_project"),
    
    path("attachments/delete/<int:attachment_id>/",views.delete_attachment,name="delete_attachment"),

]

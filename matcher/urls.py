from django.urls import path
from .views import ResumeUploadView, JobCreateView, MatchResumeToJobView, RecommendJobsView,register

from .views_auth_and_history import RegisterView, MatchHistoryView

from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path("resumes/upload/", ResumeUploadView.as_view()),
    path("jobs/create/", JobCreateView.as_view()),
    path("match/", MatchResumeToJobView.as_view()),
    path("recommend/", RecommendJobsView.as_view()),
      path("auth/register/", RegisterView.as_view()),
    path("match/history/", MatchHistoryView.as_view()),
    path("login/", TokenObtainPairView.as_view()),
    path("register/", register),
]
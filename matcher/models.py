from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User

# class Resume(models.Model):
#     file = models.FileField(upload_to="resumes/")
#     extracted_text = models.TextField(blank=True)
#     skills_json = models.JSONField(default=list, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return "Resume " + str(self.id)

class Job(models.Model):
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    skills_json = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    
    
from django.db import models
from django.contrib.auth.models import AbstractUser


from django.db import models

class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to="resumes/")
    filename = models.CharField(max_length=255, blank=True)
    extracted_text = models.TextField()
    skills_json = models.JSONField(default=list, blank=True)  # ✅ ADD THIS
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Resume " + str(self.id)

class JobDescription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="job_descriptions")
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class MatchRun(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="match_runs")
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="match_runs")
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name="match_runs")
    match_percent = models.IntegerField()
    combined_score = models.FloatField()
    tfidf_score = models.FloatField()
    embedding_score = models.FloatField()
    missing_skills = models.JSONField(default=list, blank=True)
    top_terms = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
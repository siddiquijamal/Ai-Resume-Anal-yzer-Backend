from django.contrib import admin

# Register your models here.

from .models import Resume,Job,JobDescription,MatchRun

admin.site.register(Resume)
admin.site.register(Job)
admin.site.register(JobDescription)
admin.site.register(MatchRun)

from rest_framework import serializers
from .models import Resume, Job

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ["id", "file", "extracted_text", "skills_json", "created_at"]
        read_only_fields = ["id", "extracted_text", "skills_json", "created_at"]

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ["id", "title", "company", "description", "skills_json", "created_at"]
        read_only_fields = ["id", "skills_json", "created_at"]
        
        
from rest_framework import serializers
from .models import User, Resume, JobDescription, MatchRun

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        user = User(username=validated_data["username"], email=validated_data.get("email", ""))
        user.set_password(validated_data["password"])
        user.save()
        return user

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ["id", "filename", "created_at", "extracted_text"]

class JobDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescription
        fields = ["id", "title", "company", "created_at", "text"]

class MatchRunSerializer(serializers.ModelSerializer):
    resume = ResumeSerializer(read_only=True)
    job_description = JobDescriptionSerializer(read_only=True)

    class Meta:
        model = MatchRun
        fields = [
            "id", "created_at",
            "match_percent", "combined_score", "tfidf_score", "embedding_score",
            "missing_skills", "top_terms",
            "resume", "job_description"
        ]
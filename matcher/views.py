from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework.decorators import api_view, permission_classes

from .models import Resume, Job
from .serializers import ResumeSerializer, JobSerializer

from .nlp_utils import extract_text, detect_skills, compute_match
from .services.skill_extractor import SkillExtractor
from .services.matcher import compute_match_dual
from rest_framework_simplejwt.authentication import JWTAuthentication


# ============================
# CONFIG
# ============================
MATCH_THRESHOLD = 25
skill_extractor_singleton = SkillExtractor()


# ============================
# RESUME UPLOAD
# ============================
class ResumeUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if "file" not in request.FILES:
            return Response({"error": "file is required"}, status=400)

        resume = Resume.objects.create(
            user=request.user,
            file=request.FILES["file"]
        )

        try:
            text = extract_text(resume.file.path)
        except Exception as e:
            resume.delete()
            return Response({"error": str(e)}, status=400)

        resume.extracted_text = text or ""
        resume.skills_json = detect_skills(text) or []
        resume.save()

        return Response(ResumeSerializer(resume).data, status=201)


# ============================
# JOB CREATE
# ============================
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication

class JobCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):

        # 🔒 EXTRA SAFETY CHECK (important)
        if not request.user or not request.user.is_staff:
            return Response(
                {"error": "Only admin can create jobs"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = JobSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Save job
        job = serializer.save()

        # ✅ Detect skills
        job.skills_json = detect_skills(job.description) or []
        job.save()

        return Response(
            JobSerializer(job).data,
            status=status.HTTP_201_CREATED
        )


# ============================
# MATCH
# ============================


class MatchResumeToJobView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        resume_id = request.data.get("resume_id")

        if not resume_id:
            return Response({"error": "resume_id required"}, status=400)

        # ✅ secure access (same logic, just safer)
        resume = Resume.objects.filter(id=resume_id, user=request.user).first()
        if not resume:
            return Response({"error": "Invalid resume"}, status=404)

        resume_text = (resume.extracted_text or "").strip()
        resume_skills = resume.skills_json or []

        if not resume_text:
            return Response(
                {"error": "Resume text is empty. Upload proper resume."},
                status=400
            )

        jobs = Job.objects.all()

        if not jobs.exists():
            return Response({"error": "No jobs available"}, status=400)

        matched = []
        less = []

        for job in jobs:
            try:
                job_desc = (job.description or "").strip()
                if not job_desc:
                    continue

                result = compute_match_dual(
                    resume_text,
                    job_desc,
                    resume_skills=resume_skills
                )

                print("\n========== DEBUG ==========")
                print("JOB:", job.title)
                print("TFIDF:", result["tfidf"]["score"])
                print("EMBED:", result["embedding"]["score"])
                print("FINAL %:", result["match_percent"])

                percent = result.get("match_percent", 0)

                data = {
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "match_percent": percent,
                    "tips": result.get("tips", []),

                    # ✅ same logic
                    "matched_skills": [
                        term["term"]
                        for term in result.get("tfidf", {}).get("top_terms", [])[:5]
                    ]
                }

                if percent >= MATCH_THRESHOLD:
                    matched.append(data)
                else:
                    less.append(data)

            except Exception as e:
                print("🔥 MATCH ERROR:", str(e))

                less.append({
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "match_percent": 0,
                    "tips": ["Error while matching"],
                    "matched_skills": []
                })

        # ✅ same fallback logic
        if not matched:
            matched = less[:5]

        return Response({
            "matched_jobs": matched,
            "less_relevant_jobs": less[:5],   # ⚠️ matches your frontend
            "skills": resume_skills
        })


# ============================
# RECOMMEND
# ============================
class RecommendJobsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        resume_id = request.data.get("resume_id")

        if not resume_id:
            return Response({"error": "resume_id required"}, status=400)

        # ✅ ONLY FIX: secure resume (no logic change)
        resume = Resume.objects.filter(id=resume_id, user=request.user).first()
        if not resume:
            return Response({"error": "Invalid resume"}, status=404)

        resume_text = (resume.extracted_text or "").strip()

        if not resume_text:
            return Response(
                {"error": "Resume text is empty"},
                status=400
            )

        jobs = Job.objects.all().order_by("-created_at")[:200]

        if not jobs.exists():
            return Response({"error": "No jobs available"}, status=400)

        all_jobs = []

        for job in jobs:
            try:
                job_desc = (job.description or "").strip()
                if not job_desc:
                    continue

                score = compute_match(resume_text, job_desc)

                all_jobs.append({
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "match_percent": score or 0
                })

            except Exception as e:
                print("🔥 RECOMMEND ERROR:", str(e))
                continue

        # ✅ same empty logic
        if not all_jobs:
            return Response({
                "resume_id": resume.id,
                "recommendations": [],
                "other_jobs": []
            })

        # ✅ same sorting
        all_jobs.sort(key=lambda x: x["match_percent"], reverse=True)

        return Response({
            "resume_id": resume.id,
            "recommendations": all_jobs[:10],
            "other_jobs": all_jobs[10:15]
        })


# ============================
# ANALYZE
# ============================
class AnalyzeResumeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        resume_text = request.data.get("resume_text", "")
        job_text = request.data.get("job_text", "")

        if not resume_text or not job_text:
            return Response({"error": "Both texts required"}, status=400)

        extracted = skill_extractor_singleton.extract(resume_text)

        try:
            match = compute_match_dual(
                resume_text,
                job_text,
                resume_skills=extracted["all_skills"]
            )
        except Exception as e:
            return Response({"error": str(e)}, status=500)

        return Response({
            "skills": extracted,
            "match": match
        })


# ============================
# REGISTER
# ============================
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get("username")
    password = request.data.get("password")
    email = request.data.get("email")

    if not username or not password or not email:
        return Response({"error": "All fields required"}, status=400)

    if User.objects.filter(email=email).exists():
        return Response({"error": "Email exists"}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username exists"}, status=400)

    User.objects.create_user(username=username, password=password, email=email)

    return Response({"message": "User created"}, status=201)


# ============================
# LOGIN
# ============================
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    user = authenticate(
        username=request.data.get("username"),
        password=request.data.get("password")
    )

    if not user:
        return Response({"error": "Invalid credentials"}, status=400)

    refresh = RefreshToken.for_user(user)

    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    })
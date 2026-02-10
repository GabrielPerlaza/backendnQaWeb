import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import datetime
from .forms import UserUpdateForm, ProfileUpdateForm, ProjectUploadForm
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg
from django.utils.timezone import now
from .models import ChatAttachment, ChatSession, ChatMessage, Project, UsageMetric, UserProfile
import time
from .services.ai_client import generate_test_cases
from django.http import StreamingHttpResponse
from .services.ai_client import generate_project_test_cases
from .services.ai_client import generate_test_cases_stream
import pdfplumber
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import markdown
from django.utils.safestring import mark_safe




# -------------------------
# AUTH
# -------------------------
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# -------------------------
# DASHBOARD
# -------------------------
@login_required
def dashboard_view(request):
    user = request.user

    # -------------------------
    # MÉTRICAS GENERALES
    # -------------------------
    total_chats = ChatSession.objects.filter(user=user).count()

    total_cases = ChatMessage.objects.filter(
        chat__user=user,
        is_user=False,
        success=True
    ).count()

    total_projects = Project.objects.filter(user=user).count()

    metrics = UsageMetric.objects.filter(user=user)

    time_saved = metrics.aggregate(
        total=Sum("estimated_time_saved_minutes")
    )["total"] or 0

    accuracy = metrics.aggregate(
        avg=Avg("estimated_accuracy")
    )["avg"] or 0

    # -------------------------
    # ÚLTIMA ACTIVIDAD
    # -------------------------
    last_message = ChatMessage.objects.filter(
        chat__user=user
    ).order_by("-created_at").first()

    # -------------------------
    # CONTEXTO
    # -------------------------
    context = {
        "total_cases": total_cases,
        "total_projects": total_projects,
        "time_saved": time_saved,
        "accuracy": round(accuracy, 1),
        "last_activity": last_message,
    }

    return render(request, "dashboard.html", context)


@login_required
def dashboard_metrics_api(request):
    user = request.user

    metrics = UsageMetric.objects.filter(user=user)

    data = {
        "total_cases": metrics.aggregate(
            total=Sum("total_ai_responses")
        )["total"] or 0,

        "total_projects": Project.objects.filter(user=user).count(),

        "time_saved": metrics.aggregate(
            total=Sum("estimated_time_saved_minutes")
        )["total"] or 0,

        "accuracy": round(
            metrics.aggregate(avg=Avg("estimated_accuracy"))["avg"] or 0,
            1
        ),

        "last_activity": (
            ChatMessage.objects
            .filter(chat__user=user)
            .order_by("-created_at")
            .values("content", "created_at")
            .first()
        )
    }

    return JsonResponse(data)

@login_required
def dashboard_charts_api(request):
    user = request.user

    daily = (
        UsageMetric.objects
        .filter(user=user)
        .values("date")
        .annotate(cases=Sum("total_ai_responses"))
        .order_by("date")
    )

    projects = (
        UsageMetric.objects
        .filter(user=user, project__isnull=False)
        .values("project__name")
        .annotate(cases=Sum("total_ai_responses"))
    )

    return JsonResponse({
        "daily": list(daily),
        "projects": list(projects),
    })

# -------------------------
# CHAT
# -------------------------
@login_required
def chat_view(request, chat_id=None):

    if not chat_id:
        chat = ChatSession.objects.create(user=request.user, title="Nuevo Chat")
        return redirect("chat", chat_id=chat.id)

    chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)

    messages = chat.messages.all()

    for msg in messages:
        if not msg.is_user:
            msg.rendered_html = mark_safe(
                markdown.markdown(
                    msg.content,
                    extensions=["extra", "nl2br"]
                )
            )
        else:
            msg.rendered_html = msg.content

    return render(request, "chat.html", {
        "chat": chat,
        "messages": messages,
        "attachments": chat.attachments.all(),
        "chats": ChatSession.objects.filter(user=request.user).order_by("-created_at")
    })

@login_required
def generated_cases_view(request):
    chat_id = request.GET.get("chat_id")  # <-- guardamos chat actual si viene

    # Traer todos los proyectos del usuario que tengan casos generados
    projects_with_cases = Project.objects.filter(
        user=request.user,
    ).exclude(test_cases="")  # solo los que tienen casos

    return render(request, "generated_cases.html", {
        "projects": projects_with_cases,
        "chat_id": chat_id,  # <-- pasamos al template
        "chats": ChatSession.objects.filter(user=request.user).order_by("-created_at")
    })


# -------------------------
# PROYECTOS
# -------------------------
@login_required
def projects_view(request):
    projects = Project.objects.filter(user=request.user)
    return render(request, "projects.html", {"projects": projects})

import zipfile

ALLOWED_EXTENSIONS = (
    ".py", ".js", ".ts", ".java", ".cs",
    ".html", ".css", ".sql",
    ".md", ".txt"
)

MAX_PROJECT_CHARS = 6000

def is_allowed_file(filename: str) -> bool:
    return filename.lower().endswith(ALLOWED_EXTENSIONS)

def extract_project_content(file) -> str:
    content = ""

    with zipfile.ZipFile(file) as z:
        for info in z.infolist():
            if info.is_dir():
                continue

            if not is_allowed_file(info.filename):
                continue

            with z.open(info) as f:
                try:
                    text = f.read().decode("utf-8", errors="ignore")
                except:
                    continue

            content += f"\n\n### FILE: {info.filename}\n{text}"

            if len(content) >= MAX_PROJECT_CHARS:
                break

    return content[:MAX_PROJECT_CHARS]


def extract_pdf_text(file) -> str:
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


@login_required
def upload_project_view(request):
    if request.method == "POST":
        form = ProjectUploadForm(request.POST, request.FILES)

        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user

            # 🔴 VALIDACIÓN NOMBRE DUPLICADO
            if Project.objects.filter(user=request.user, name=project.name).exists():
                return render(request, "upload_project.html", {
                    "form": form,
                    "error": "Ya existe un proyecto con este nombre. Usa un nombre diferente."
                })

            # 🔹 leer archivo para generar casos
            content = ""

            if project.file:
                filename = project.file.name.lower()

                if filename.endswith(".zip"):
                    content = extract_project_content(project.file)
                elif filename.endswith(".pdf"):
                    content = extract_pdf_text(project.file)
                else:
                    try:
                        content = project.file.read().decode("utf-8", errors="ignore")
                    except:
                        content = ""

            content = content[:MAX_PROJECT_CHARS]

            if len(content.strip()) < 200:
                return render(request, "upload_project.html", {
                    "form": form,
                    "error": "El archivo no contiene texto suficiente para generar casos de prueba."
            })

            print("contenido" + content)
            print("enviando....")
            # 🔥 generar casos de prueba
            test_cases = generate_project_test_cases(content)

            project.test_cases = test_cases
            project.save()  # ✅ aquí ya guarda archivo + proyecto

            UsageMetric.objects.create(
                user=request.user,
                project=project,
                total_ai_responses=test_cases.count("ID:"),
                estimated_time_saved_minutes=10,
                estimated_accuracy=0.9
            )


            chat_id = request.GET.get("chat_id")

            html_cases = markdown.markdown(
                test_cases,
                extensions=["extra", "nl2br", "sane_lists"]
            )

            return render(request, "project_test_cases.html", {
                "project": project,
                "project_name": project.name,
                "test_cases_html": html_cases,
                "chat_id": chat_id
            })

    else:
        form = ProjectUploadForm()

    return render(request, "upload_project.html", {
        "form": form
    })

@login_required
def project_test_cases_view(request, project_id):
    from .services.ai_client import generate_test_cases

    project = get_object_or_404(Project, id=project_id, user=request.user)

    if not project.test_cases:
        content = project.description or ""
        if project.file:
            try:
                content = project.file.read().decode("utf-8")
            except Exception:
                project.file.seek(0)
                content = str(project.file.read())

        # Generar casos de prueba usando FastAPI
        test_cases = generate_test_cases(content, max_tokens=800)

        project.test_cases = test_cases
        project.save()
    else:
        test_cases = project.test_cases
        chat_id = request.GET.get("chat_id")  # si viene en la URL
        print("Chat ID recibido:", chat_id)

        html_cases = markdown.markdown(
            test_cases,
            extensions=["extra", "nl2br", "sane_lists"]
        )

        return render(request, "project_test_cases.html", {
            "project": project,
            "project_name": project.name,
            "test_cases_html": html_cases,
            "chat_id": chat_id
        })


# -------------------------
# HISTORIAL
# -------------------------
@login_required
def history_view(request):
    chats = ChatSession.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "history.html", {
        "chats": chats
    })


# -------------------------
# MÉTRICAS
# -------------------------
@login_required
def metrics_view(request):
    user = request.user

    # -------------------------
    # FILTROS DE FECHA
    # -------------------------
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    metrics_qs = UsageMetric.objects.filter(user=user)

    if start_date:
        metrics_qs = metrics_qs.filter(date__gte=start_date)

    if end_date:
        metrics_qs = metrics_qs.filter(date__lte=end_date)

    # -------------------------
    # KPIs
    # -------------------------
    total_cases = metrics_qs.aggregate(
        total=Sum("total_ai_responses")
    )["total"] or 0

    total_chats = ChatSession.objects.filter(
        user=user
    ).count()

    total_projects = Project.objects.filter(user=user).count()

    time_saved = metrics_qs.aggregate(
        total=Sum("estimated_time_saved_minutes")
    )["total"] or 0

    accuracy = metrics_qs.aggregate(
        avg=Avg("estimated_accuracy")
    )["avg"] or 0

    # -------------------------
    # MÉTRICAS DIARIAS
    # -------------------------
    daily_metrics = list(
        metrics_qs
        .values("date")
        .annotate(
            cases=Sum("total_ai_responses"),
            time_saved=Sum("estimated_time_saved_minutes")
        )
        .order_by("date")
    )

    # -------------------------
    # MÉTRICAS POR PROYECTO
    # -------------------------
    project_metrics = list(
        metrics_qs
        .filter(project__isnull=False)
        .values("project__name")
        .annotate(
            cases=Sum("total_ai_responses"),
            time_saved=Sum("estimated_time_saved_minutes"),
            accuracy=Avg("estimated_accuracy")
        )
        .order_by("-cases")
    )

    return render(request, "metrics.html", {
        "total_cases": total_cases,
        "total_chats": total_chats,
        "total_projects": total_projects,
        "time_saved": time_saved,
        "accuracy": round(accuracy, 1),
        "daily_metrics": daily_metrics,
        "project_metrics": project_metrics,
        "start_date": start_date,
        "end_date": end_date,
    })



# -------------------------
# PERFIL
# -------------------------
@login_required
def profile_view(request):
    user = request.user

    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=profile
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect("profile")

    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, "profile.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })


# @login_required
def upload_attachment_view(request, chat_id):
    chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)

    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        file_type = request.POST.get("file_type", "image")

        # 🔴 SOLO IMÁGENES
        if file_type != "image":
            return JsonResponse(
                {"success": False, "error": "Solo se permiten imágenes"},
                status=400
            )

        attachment = ChatAttachment.objects.create(
            chat=chat,
            file=file,
            file_type="image"
        )

        return JsonResponse({
            "success": True,
            "file_name": attachment.file.name.split("/")[-1],
            "file_url": attachment.file.url,
            "file_type": "image"
        })

    return JsonResponse({"success": False}, status=400)


def is_test_case_request(text: str) -> bool:
    keywords = [
        "caso de prueba",
        "casos de prueba",
        "test case",
        "verificar",
        "validar",
        "escenario"
    ]
    return any(k in text.lower() for k in keywords)



# ==========================
# 🔥 NIVEL 7 – STREAM CHAT
# ==========================
@login_required
def chat_stream_view(request, chat_id):
    chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)
    user_message = request.GET.get("message", "").strip()

    if not user_message:
        return StreamingHttpResponse("", content_type="text/plain")

    # Guardar mensaje del usuario
    ChatMessage.objects.create(
        chat=chat,
        is_user=True,
        content=user_message
    )

    # Título automático si es el primer mensaje
    if not chat.title or chat.title.lower() == "nuevo chat":
        chat.title = user_message.strip()[:50]
        chat.save(update_fields=["title"])

    # CONTEXTO DE ARCHIVOS (si existieran)
    context = ""

    start_time = time.time()

    def stream():
        ai_text = ""

        for line in generate_test_cases_stream({
            "requirement": user_message,
            "context": context
        }):
            # Espacios y saltos de línea conservados para que se vea bonito
            ai_text += line
            yield line   # línea completa con salto de línea

        # Guardar respuesta completa
        response_time_ms = int((time.time() - start_time) * 1000)
        ChatMessage.objects.create(
            chat=chat,
            is_user=False,
            content=ai_text.strip(),
            success=True,
            language="es",
            response_time_ms=response_time_ms
        )

    return StreamingHttpResponse(stream(), content_type="text/plain")

@login_required
def download_project_test_cases(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)

    if not project.test_cases:
        return HttpResponse("Este proyecto no tiene casos de prueba", status=404)

    # 1️⃣ Markdown → HTML
    html = markdown.markdown(
        project.test_cases,
        extensions=["extra", "nl2br", "sane_lists"]
    )

    # 2️⃣ HTML compatible con ReportLab
    html = (
        html
        .replace("<strong>", "<b>")
        .replace("</strong>", "</b>")
        .replace("<em>", "<i>")
        .replace("</em>", "</i>")
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    story = []

    # 3️⃣ Separar por párrafos HTML
    for block in html.split("\n"):
        if block.strip():
            story.append(
                Paragraph(block, styles["Normal"])
            )

    doc.build(story)

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{project.name}_casos_de_prueba.pdf"'
    )

    return response

@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    project.delete()
    return redirect("projects")

@login_required
def delete_attachment(request, attachment_id):
    att = get_object_or_404(ChatAttachment, id=attachment_id, chat__user=request.user)
    att.file.delete()
    att.delete()
    return JsonResponse({"success": True})


@login_required
def chat_files_view(request):
    files = ChatAttachment.objects.filter(
        chat__user=request.user,
        file_type="image"
    ).order_by("-created_at")

    return render(request, "chat_files.html", {
        "files": files
    })


@login_required
def delete_chat_file(request, file_id):
    file = get_object_or_404(
        ChatAttachment,
        id=file_id,
        chat__user=request.user
    )
    file.delete()
    return redirect("chat_files")

@login_required
def delete_project_file(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    project.file.delete()
    project.save()
    return redirect("projects")



@login_required
def delete_project(request, project_id):
    project = get_object_or_404(
        Project,
        id=project_id,
        user=request.user
    )
    project.delete()
    return redirect("projects")

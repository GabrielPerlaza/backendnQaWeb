from django.db import models
from django.contrib.auth.models import User


# -------------------------
# PROYECTOS
# -------------------------
class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # ✅ ARCHIVO DEL PROYECTO
    file = models.FileField(
        upload_to="projects/",
        blank=True,
        null=True
    )

    test_cases = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ("user", "name")


# -------------------------
# SESIÓN DE CHAT
# -------------------------
class ChatSession(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chats"
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chats"
    )
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Métricas de chat
    total_messages = models.PositiveIntegerField(default=0)
    total_ai_messages = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} ({self.user.username})"


# -------------------------
# MENSAJES DEL CHAT
# -------------------------
class ChatMessage(models.Model):
    chat = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    is_user = models.BooleanField(default=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Métricas IA
    response_time_ms = models.PositiveIntegerField(
        null=True, blank=True
    )
    prompt_tokens = models.PositiveIntegerField(
        null=True, blank=True
    )
    completion_tokens = models.PositiveIntegerField(
        null=True, blank=True
    )
    language = models.CharField(
        max_length=20,
        default="es"
    )
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        role = "Usuario" if self.is_user else "IA"
        return f"{role}: {self.content[:40]}"


# -------------------------
# MÉTRICAS AGREGADAS (DASHBOARD)
# -------------------------
class UsageMetric(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="metrics"
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    date = models.DateField(auto_now_add=True)

    total_chats = models.PositiveIntegerField(default=0)
    total_messages = models.PositiveIntegerField(default=0)
    total_ai_responses = models.PositiveIntegerField(default=0)

    estimated_time_saved_minutes = models.PositiveIntegerField(default=0)
    estimated_accuracy = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ('user', 'project', 'date')
    
    def __str__(self):
        return f"Métricas {self.user.username} - {self.date}"

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    avatar = models.ImageField(
        upload_to="avatars/",
        default="avatars/default.png",
        blank=True
    )

    bio = models.TextField(blank=True)
    company = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=100, default="QA Engineer")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"

class ChatAttachment(models.Model):
    chat = models.ForeignKey(
        ChatSession,
        related_name="attachments",
        on_delete=models.CASCADE
    )
    file = models.FileField(upload_to="chat_files/")
    file_type = models.CharField(max_length=20)  # document, image, file
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

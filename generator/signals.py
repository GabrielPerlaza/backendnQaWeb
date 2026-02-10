import time
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import localdate
from django.contrib.auth.models import User
from .models import ChatMessage, UsageMetric, UserProfile

@receiver(post_save, sender=ChatMessage)
def update_metrics_on_message(sender, instance, created, **kwargs):
    if not created:
        return

    chat = instance.chat
    user = chat.user
    project = chat.project

    # -------------------------
    # Obtener o crear métrica diaria de manera segura
    # -------------------------
    metrics = UsageMetric.objects.filter(
        user=user,
        project=project,
        date=localdate()
    ).order_by('id')

    if metrics.exists():
        metric = metrics.first()

        # Limpiar posibles duplicados antiguos
        duplicates = metrics.exclude(id=metric.id)
        if duplicates.exists():
            duplicates.delete()
    else:
        metric = UsageMetric.objects.create(
            user=user,
            project=project,
            date=localdate(),
            total_messages=0,
            total_ai_responses=0,
            estimated_time_saved_minutes=0,
            estimated_accuracy=0
        )

    # -------------------------
    # Actualizar métricas del chat
    # -------------------------
    chat.total_messages += 1
    if not instance.is_user:
        chat.total_ai_messages += 1
        metric.total_ai_responses += 1
        metric.estimated_time_saved_minutes += max(instance.response_time_ms // 1000, 1)
        metric.estimated_accuracy = min(metric.estimated_accuracy + 0.3, 98)

    chat.save(update_fields=["total_messages", "total_ai_messages"])

    # -------------------------
    # Actualizar métricas diarias adicionales
    # -------------------------
    metric.total_messages += 1
    if not instance.is_user:
        metric.estimated_time_saved_minutes += 5
        metric.estimated_accuracy = min(metric.estimated_accuracy + 0.5, 95)

    metric.save()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

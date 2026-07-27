from rest_framework import viewsets

from .models import Appointment, BotStatistics, Event, TelegramUser
from .serializers import (
    AppointmentSerializer,
    BotStatisticsSerializer,
    EventSerializer,
    TelegramUserSerializer,
)


class TelegramUserViewSet(viewsets.ModelViewSet):
    queryset = TelegramUser.objects.all()
    serializer_class = TelegramUserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        telegram_id = self.request.query_params.get("telegram_id")
        if telegram_id:
            queryset = queryset.filter(telegram_id=telegram_id)
        return queryset


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.select_related("owner")
    serializer_class = EventSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        owner_telegram_id = self.request.query_params.get("owner_telegram_id")
        date = self.request.query_params.get("date")
        is_public = self.request.query_params.get("is_public")

        if owner_telegram_id:
            queryset = queryset.filter(owner__telegram_id=owner_telegram_id)
        if date:
            queryset = queryset.filter(date=date)
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() in ("1", "true", "yes"))

        return queryset


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related("event", "event__owner")
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get("user_id")
        status = self.request.query_params.get("status")
        appointment_date = self.request.query_params.get("date")

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if status:
            queryset = queryset.filter(status=status)
        if appointment_date:
            queryset = queryset.filter(appointment_date=appointment_date)

        return queryset


class BotStatisticsViewSet(viewsets.ModelViewSet):
    queryset = BotStatistics.objects.all().order_by("-date")
    serializer_class = BotStatisticsSerializer

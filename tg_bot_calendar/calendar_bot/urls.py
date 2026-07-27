from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    AppointmentViewSet,
    BotStatisticsViewSet,
    EventViewSet,
    TelegramUserViewSet,
)


router = DefaultRouter()
router.register("users", TelegramUserViewSet)
router.register("events", EventViewSet)
router.register("appointments", AppointmentViewSet)
router.register("statistics", BotStatisticsViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

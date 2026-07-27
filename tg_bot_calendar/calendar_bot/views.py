from django.core import signing
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_GET

from .services import export_user_events, parse_event_export_token


EVENT_EXPORT_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24


@require_GET
def export_events_view(request):
    token = request.GET.get("token")
    if not token:
        return HttpResponseBadRequest("Missing export token.")

    try:
        telegram_id = parse_event_export_token(
            token,
            max_age=EVENT_EXPORT_TOKEN_MAX_AGE_SECONDS,
        )
    except (KeyError, TypeError, ValueError, signing.BadSignature):
        return HttpResponseForbidden("Invalid export token.")

    try:
        export_result = export_user_events(
            telegram_id,
            request.GET.get("format", "json"),
        )
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))

    response = HttpResponse(
        export_result["content"],
        content_type=export_result["content_type"],
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{export_result["filename"]}"'
    )
    return response

"""Serve the built React app (frontend/dist) from Django in production.

WhiteNoise serves the hashed assets (``WHITENOISE_ROOT``); this view returns
``index.html`` for any other non-API path so client-side URLs keep working.
"""

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def spa_index(request, path: str = ""):
    index = settings.FRONTEND_DIST_DIR / "index.html"
    if not index.exists():
        return HttpResponse(
            "Frontend not built. Run `npm run build` in frontend/ or use the Vite dev server.",
            status=404,
            content_type="text/plain",
        )
    response = FileResponse(index.open("rb"), content_type="text/html")
    response["Cache-Control"] = "no-cache"
    return response

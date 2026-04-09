from datetime import date

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render, redirect


def landing_page(request):
    return render(request, 'landing.html', {'current_year': date.today().year})


# Custom error handlers
handler404 = lambda request, exception: render(request, 'errors/404.html', status=404)
handler500 = lambda request: render(request, 'errors/500.html', status=500)
handler403 = lambda request, exception: render(request, 'errors/403.html', status=403)

urlpatterns = [
    path('', landing_page, name='landing'),
    path('admin/', admin.site.urls),

    # App URLs (SSR)
    path('', include('apps.accounts.urls')),
    # path('', include('apps.assistant.urls')),
    path('', include('apps.cards.urls')),
    path('', include('apps.categories.urls')),
    # path('', include('apps.reports.urls')),
    path('', include('apps.transactions.urls')),

    # API URLs
    path('api/v1/accounts/', include('apps.accounts.api_urls')),
    path('api/v1/categories/', include('apps.categories.api_urls')),
    path('api/v1/cards/', include('apps.cards.api_urls')),

    # OAuth (allauth)
    path('accounts/', include('allauth.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

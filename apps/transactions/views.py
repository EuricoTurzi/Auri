from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View


class DashboardView(LoginRequiredMixin, View):
    """Placeholder — será implementado na spec de transactions."""

    def get(self, request):
        return render(request, 'transactions/dashboard.html')

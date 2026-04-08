from django.shortcuts import redirect
from django.urls import reverse


class FirstAccessMiddleware:
    """
    Redireciona usuários com is_first_access=True para a página de troca de senha.
    Permite acesso apenas à página de troca de senha e logout.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.user.is_first_access
        ):
            allowed_urls = [
                reverse('accounts:change_password'),
                reverse('accounts:logout'),
            ]
            if request.path not in allowed_urls:
                return redirect('accounts:change_password')

        return self.get_response(request)

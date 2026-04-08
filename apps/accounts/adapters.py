from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Adapter para marcar is_first_access=False em usuários criados via OAuth."""

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.is_first_access = False
        user.save(update_fields=['is_first_access', 'updated_at'])
        return user

ALLOWED_EMAIL_DOMAIN = "ceew.in"


def is_allowed_user(user) -> bool:
    """user: st.user (populated by st.login() once [auth] is configured in secrets.toml)."""
    email = getattr(user, "email", None)
    if not email:
        return False
    return email.lower().endswith(f"@{ALLOWED_EMAIL_DOMAIN}")

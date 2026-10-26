from collections.abc import Mapping
from urllib.parse import urlparse

ALLOWED_EMAIL_DOMAIN = "ceew.in"


def _claims(user) -> dict:
    if hasattr(user, "to_dict"):
        return user.to_dict()
    if isinstance(user, Mapping):
        return dict(user)
    return vars(user)


def is_allowed_user(user) -> bool:
    """user: st.user (populated by st.login() once [auth] is configured in secrets.toml).

    Google returns `email_verified` and, for Workspace accounts, `hd` (hosted
    domain). Checking them stops a personal account that merely has an
    "@ceew.in"-looking alias from getting in."""
    claims = _claims(user)
    email = claims.get("email")
    if not email:
        return False
    if not email.lower().endswith(f"@{ALLOWED_EMAIL_DOMAIN}"):
        return False
    if claims.get("email_verified") is False:
        return False
    hosted_domain = claims.get("hd")
    if hosted_domain is not None and hosted_domain.lower() != ALLOWED_EMAIL_DOMAIN:
        return False
    return True


def canonical_origin(redirect_uri: str, port: int | None = None) -> str:
    """scheme://host:port of the OAuth redirect_uri (with Streamlit's `{port}` placeholder filled in)."""
    if port is not None:
        redirect_uri = redirect_uri.replace("{port}", str(port))
    parsed = urlparse(redirect_uri)
    return f"{parsed.scheme}://{parsed.netloc}"


def origin_mismatch(current_url: str | None, redirect_uri: str, port: int | None = None) -> str | None:
    """Returns the canonical origin if the app is being viewed from a different
    host than the OAuth callback (e.g. localhost vs 127.0.0.1), else None.

    Google sends the user back to the redirect_uri's host, but the login-state
    cookie is scoped to the host the user started on. When the two differ the
    callback can't find its state and the user silently lands back on the
    login screen - the "SSO doesn't work" loop."""
    if not current_url:
        return None
    expected = canonical_origin(redirect_uri, port)
    parsed = urlparse(current_url)
    if f"{parsed.scheme}://{parsed.netloc}" != expected:
        return expected
    return None

from config.access import is_allowed_user, origin_mismatch


def test_workspace_account_allowed():
    assert is_allowed_user({"email": "a.b@ceew.in", "email_verified": True, "hd": "ceew.in"})


def test_other_domain_rejected():
    assert not is_allowed_user({"email": "someone@gmail.com", "email_verified": True})


def test_unverified_email_rejected():
    assert not is_allowed_user({"email": "a.b@ceew.in", "email_verified": False})


def test_wrong_hosted_domain_rejected():
    assert not is_allowed_user({"email": "a.b@ceew.in", "email_verified": True, "hd": "example.org"})


def test_missing_email_rejected():
    assert not is_allowed_user({})


def test_localhost_vs_loopback_is_a_mismatch():
    redirect = "http://127.0.0.1:8501/oauth2callback"
    assert origin_mismatch("http://localhost:8501/", redirect) == "http://127.0.0.1:8501"
    assert origin_mismatch("http://127.0.0.1:8501/daily-update", redirect) is None


def test_port_placeholder():
    redirect = "http://localhost:{port}/oauth2callback"
    assert origin_mismatch("http://localhost:8599/", redirect, port=8599) is None


def test_unknown_url_is_not_a_mismatch():
    assert origin_mismatch(None, "http://127.0.0.1:8501/oauth2callback") is None

import re
import logging
import requests


class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token: str):
        self.token = str(token)

    def __call__(self, r):
        r.headers["Authorization"] = self.token
        return r


def make_session(token: str) -> requests.Session:
    """Create an authenticated requests session."""
    session = requests.Session()
    session.auth = TokenAuth(token)
    return session


def setup_logging(logger: logging.Logger, loglvl: int) -> None:
    """Configure a logger with a standard formatter and stream handler."""
    formatter = logging.Formatter(
        "%(asctime)s  %(name)s  %(lineno)-4d  %(levelname)-9s :: %(message)s"
    )
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.setLevel(loglvl)
    logger.addHandler(ch)
    logger.propagate = False


def validate_url(base_url: str) -> str | None:
    """Return an error string if base_url is not a valid HTTP/HTTPS URL, else None."""
    if not base_url.startswith(("http://", "https://")):
        return f"--base_url does not look like a valid URL: '{base_url}'"
    return None


def validate_token(token: str) -> str | None:
    """Return an error string if token is not a 40-character hex string, else None."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", token):
        return "--token must be a 40-character hexadecimal string."
    return None

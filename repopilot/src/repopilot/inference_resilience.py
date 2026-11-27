"""HTTP transport for the Space dispatcher."""

from __future__ import annotations

import urllib.request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("Provider redirects are prohibited")


def build_safe_opener(*, allow_env_proxy: bool = False) -> urllib.request.OpenerDirector:
    """Ensure both Ollama and OpenAI-compatible paths bypass ambient proxies by default."""
    if allow_env_proxy:
        return urllib.request.build_opener(_NoRedirect())
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

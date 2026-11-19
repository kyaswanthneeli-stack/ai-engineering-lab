"""Read a public GitHub issue via the official REST API (read-only)."""
import json
import re
import urllib.request

ISSUE_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)/?$")
class IssueFetchError(ValueError):
    pass

def fetch_public_issue(url: str, transport=None) -> dict:
    match = ISSUE_URL.fullmatch(url)
    if not match or len(url) > 250:
        raise IssueFetchError("Expected a public github.com/{owner}/{repo}/issues/{number} URL")
    owner, repo, number = match.groups()
    endpoint = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
    if transport is None:
        def transport(request):
            with urllib.request.urlopen(request, timeout=12) as response:
                return response.read(150_001)
    request = urllib.request.Request(endpoint,headers={"Accept":"application/vnd.github+json","User-Agent":"RepoPilot/0.3"})
    try:
        data = transport(request)
        if len(data) > 150_000:
            raise IssueFetchError("Issue response too large")
        payload=json.loads(data)
    except IssueFetchError:
        raise
    except Exception as exc:
        raise IssueFetchError("Could not retrieve issue") from exc
    if not isinstance(payload,dict) or "pull_request" in payload or not isinstance(payload.get("title"),str) or not isinstance(payload.get("body"),(str,type(None))):
        raise IssueFetchError("Not an ordinary GitHub issue")
    body=(payload.get("body") or "")[:9000]
    title=payload["title"][:200]
    return {"issue_id":f"{owner}/{repo}#{number}","repository":f"{owner}/{repo}","url":url,"title":title,"body":body,"text":f"{title}\n\n{body}"}

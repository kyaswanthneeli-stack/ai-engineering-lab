"""Self-contained, escaped, offline review dashboard. No live server needed."""
import html
import json
from pathlib import Path
from .test_evidence import check_verification_report

def _json(data):
    return html.escape(json.dumps(data,indent=2,ensure_ascii=False),quote=True)

def render_dashboard(report: dict, output: Path, proposal:dict|None=None, issue:dict|None=None) -> Path:
    if not isinstance(report,dict):
        raise ValueError("Expected a report")
    before=report.get("before",{}) or {}
    after=report.get("after",{}) or {}
    try:
        check_verification_report(report)
    except ValueError:
        verified=False
    else:
        verified=True
    status="VERIFIED: fail before / pass after" if verified else "UNVERIFIED / FAILED"
    badge="#8be6b2" if verified else "#ffd0a2"
    sections=[
        ("GitHub issue",issue or {"note":"No live GitHub issue was fetched for this run"}),
        ("Proposed patch",proposal or {"note":"No model proposal attached; fixture/approved patch may have been used"}),
        ("Baseline tests",report.get("baseline",{})),
        ("Before fix: reproduction",before),
        ("After fix: regression",after),
        ("Execution evidence",report)
    ]
    cards="".join(f'<section><h2>{html.escape(name)}</h2><pre>{_json(content)}</pre></section>' for name,content in sections)
    doc=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RepoPilot · Run evidence</title><style>
:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#0b1020;color:#f5f7ff;font:15px/1.6 system-ui,Arial,sans-serif}}main{{max-width:1080px;margin:auto;padding:44px 24px}}header{{border-bottom:1px solid #2e3853;padding-bottom:26px}}.tag{{font-size:12px;color:{badge};letter-spacing:.08em;font-weight:700}}h1{{font-size:clamp(30px,4vw,50px);margin:8px 0}}p{{color:#b7c0d8}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:16px;margin-top:24px}}section{{min-width:0;background:#151d31;border:1px solid #35415e;border-radius:16px;padding:18px}}section:last-child{{grid-column:1/-1}}h2{{font-size:16px;margin:0 0 12px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 ui-monospace,SFMono-Regular,monospace;color:#d7e1ff;max-height:410px;overflow:auto}}.notice{{border-left:3px solid #7898ff;padding-left:14px}}</style></head><body><main><header><div class="tag">{html.escape(status)}</div><h1>RepoPilot · Verification evidence</h1><p class="notice">This page is generated from a local report. It is not a live agent, and it does not imply a model call or draft PR unless the evidence explicitly records one.</p></header><div class="grid">{cards}</div></main></body></html>'''
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(doc,encoding="utf-8")
    return output

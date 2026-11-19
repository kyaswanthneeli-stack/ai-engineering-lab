"""Benchmark report aggregation; never conflates fixtures with AI issue resolutions."""
import json
import statistics
from pathlib import Path

def aggregate(records:list[dict],dataset_name:str="unlabeled") -> dict:
    if not isinstance(records,list):
        raise ValueError("Expected a list")
    total=len(records)
    verified=sum(1 for x in records if x.get("outcome")=="verified_in_sandbox" and x.get("before",{}).get("exit_code") not in (0,None) and x.get("after",{}).get("exit_code")==0)
    model_attempts=sum(1 for x in records if x.get("model_generated_proposal") is True)
    live_resolved=sum(1 for x in records if x.get("model_generated_proposal") is True and x.get("outcome")=="verified_in_sandbox" and x.get("before",{}).get("exit_code") not in (0,None) and x.get("after",{}).get("exit_code")==0)
    times=[x["elapsed_ms"] for x in records if isinstance(x.get("elapsed_ms"),(int,float)) and x["elapsed_ms"]>=0]
    return {
        "dataset":dataset_name,"attempts":total,"verified_patches":verified,
        "model_generated_attempts":model_attempts,
        "model_generated_verified":live_resolved,
        "model_success_rate":round(live_resolved/model_attempts,4) if model_attempts else None,
        "verification_rate_all_proposals":round(verified/total,4) if total else None,
        "median_elapsed_ms":round(statistics.median(times)) if times else None,
        "caveat":"This is an aggregation of supplied run records. Fixture verification is not autonomous issue resolution. Missing attempts are not treated as successes."
    }

def read_and_aggregate(paths:list[Path],dataset_name:str="unlabeled")->dict:
    if not paths:
        return aggregate([],dataset_name)
    return aggregate([json.loads(p.read_text(encoding="utf-8")) for p in paths],dataset_name)

def write_report(records:list[dict],path:Path,dataset_name:str="unlabeled"):
    result=aggregate(records,dataset_name)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result

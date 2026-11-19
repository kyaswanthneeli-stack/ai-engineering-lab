"""Select public SWE-bench Lite tasks reproducibly; DOES NOT score them.

Full SWE-bench evaluation requires each task's base commit, environment,
test patch and official Docker evaluation harness, not RepoPilot's toy runner.
"""
import json
from pathlib import Path

DATASET="SWE-bench/SWE-bench_Lite"

def select_instances(limit:int=12,seed:int=73,loader=None)->list[dict]:
    if not 1<=limit<=30:
        raise ValueError("Select 1 to 30 issues")
    if loader is None:
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise RuntimeError("Install optional dependency: pip install datasets") from exc
        dataset=load_dataset(DATASET,split="test")
    else:
        dataset=loader(DATASET,"test")
    import random
    order=list(range(len(dataset)))
    random.Random(seed).shuffle(order)
    selected=[]
    for i in order[:limit]:
        sample=dataset[i]
        selected.append({
            "instance_id":sample["instance_id"],
            "repo":sample["repo"],
            "base_commit":sample["base_commit"],
            "status":"not_attempted",
            "model_result":None,
            "patch_file":None
        })
    return selected

def write_manifest(output:Path,limit:int=12,seed:int=73,loader=None)->dict:
    tasks=select_instances(limit,seed,loader=loader)
    result={"dataset":DATASET,"split":"test","seed":seed,"selection_count":len(tasks),"status":"selected_not_evaluated","tasks":tasks,
            "notice":"No issue attempts or successful resolutions are claimed. Use the official SWE-bench harness to evaluate model patches."}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result

import argparse,random,json
from .common import DATA,read,write
def main():
 p=argparse.ArgumentParser();p.add_argument("--train",type=float,default=.8);p.add_argument("--val",type=float,default=.1);p.add_argument("--seed",type=int,default=42);a=p.parse_args()
 if a.train<=0 or a.val<0 or a.train+a.val>=1:raise SystemExit("Invalid ratios")
 chunks=read(DATA/"processed/code_chunks.jsonl");qas=read(DATA/"qa/qa_candidates.jsonl")
 repos=sorted({c["repo_id"] for c in chunks});random.Random(a.seed).shuffle(repos)
 nt=max(1,int(len(repos)*a.train)) if repos else 0;nv=int(len(repos)*a.val)
 sets={"train":set(repos[:nt]),"validation":set(repos[nt:nt+nv]),"test":set(repos[nt+nv:])}
 mapping={r:s for s,rs in sets.items() for r in rs}
 for c in chunks:c["split"]=mapping[c["repo_id"]]
 for s in ["train","validation","test"]:write(DATA/f"splits/{'val' if s=='validation' else s}_chunks.jsonl",[c for c in chunks if c["split"]==s])
 for q in qas:q["split"]=mapping.get(q["repo_id"])
 for s in ["train","validation","test"]:write(DATA/f"splits/{'val' if s=='validation' else s}_pairs.jsonl",[q for q in qas if q.get("split")==s])
 manifest={"seed":a.seed,"repository_ids":{s:sorted(rs) for s,rs in sets.items()},"counts":{s:len(rs) for s,rs in sets.items()},"warning":"Tiny repository counts make evaluation statistically weak."}
 (DATA/"splits/split_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8");print(manifest["counts"])
if __name__=="__main__":main()

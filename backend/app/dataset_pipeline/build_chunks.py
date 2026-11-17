import ast
from pathlib import Path
from dataset_pipeline.build_chunks import py_chunks, java_chunks
from .common import DATA, EXT, skip, secret, sid, read, write
def main():
 rows=[]
 for repo in read(DATA/"metadata/repositories.jsonl"):
  if repo.get("clone_status")!="success":continue
  base=DATA/"raw"/repo["repo_id"]
  for f in base.rglob("*"):
   if not f.is_file():continue
   try:
    if skip(f.relative_to(base)):continue
    text=f.read_text(encoding="utf-8")
   except Exception:continue
   if secret(text):print("[SKIP SECRET-LIKE FILE]",f);continue
   rel=f.relative_to(base).as_posix();lang=EXT[f.suffix.lower()]
   try:chunks=py_chunks(text) if lang=="python" else java_chunks(text)
   except SyntaxError:
    ls=text.splitlines();chunks=[("fallback_block",f"lines_{i+1}", "\n".join(ls[i:i+80])[:12000],i+1,min(i+80,len(ls)),[],[],[],"line_fallback") for i in range(0,len(ls),70)]
   for typ,name,code,start,end,imports,defined,used,status in chunks:
    rows.append({"schema_version":"1.0","repo_id":repo["repo_id"],"repo_full_name":repo["full_name"],"commit_sha":repo.get("commit_sha"),"file_path":rel,"language":lang,"chunk_id":sid(repo["repo_id"],repo.get("commit_sha"),rel,start,end,name),"chunk_type":typ,"chunk_name":name,"code_text":code,"start_line":start,"end_line":end,"imports":imports,"symbols_defined":defined,"symbols_used":used,"parser_status":status,"license_spdx_id":repo.get("license_spdx_id"),"licence_review_status":"needs_human_review","split":None})
 write(DATA/"processed/code_chunks.jsonl",rows);print("Chunks:",len(rows))
if __name__=="__main__":main()

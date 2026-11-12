import subprocess
from .common import DATA,read,write
def main():
 rows=read(DATA/"metadata/repositories.jsonl");out=[]
 for r in rows:
  dest=DATA/"raw"/r["repo_id"]
  try:
   if not dest.exists():subprocess.run(["git","clone","--depth","1",r["clone_url"],str(dest)],check=True)
   r["commit_sha"]=subprocess.check_output(["git","-C",str(dest),"rev-parse","HEAD"],text=True).strip();r["clone_status"]="success"
  except Exception as e:r["clone_status"]="failed";r["clone_error"]=str(e)[:300];print("[WARN]",r["full_name"],e)
  out.append(r)
 write(DATA/"metadata/repositories.jsonl",out)
if __name__=="__main__":main()

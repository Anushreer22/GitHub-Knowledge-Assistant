import argparse,os,time,requests
from dotenv import load_dotenv
from .common import DATA,write
load_dotenv()
def main():
 p=argparse.ArgumentParser();p.add_argument("--per-language",type=int,default=10);a=p.parse_args()
 api=os.getenv("GITHUB_API_URL","https://api.github.com").rstrip("/")
 token=os.getenv("GITHUB_TOKEN","").strip(); headers={"Accept":"application/vnd.github+json"}
 if token:headers["Authorization"]="Bearer "+token
 rows=[];seen=set()
 for lang in ["Python","Java"]:
  params={"q":f"language:{lang} stars:>=5 archived:false fork:false license:*","sort":"stars","order":"desc","per_page":min(a.per_language,100)}
  try:
   r=requests.get(api+"/search/repositories",headers=headers,params=params,timeout=30);r.raise_for_status()
   for x in r.json().get("items",[]):
    if x["full_name"].lower() in seen:continue
    seen.add(x["full_name"].lower());lic=x.get("license") or {}
    rows.append({"repo_id":x["full_name"].replace("/","__"),"full_name":x["full_name"],"html_url":x["html_url"],"clone_url":x["clone_url"],"default_branch":x.get("default_branch"),"language":x.get("language"),"stars":x.get("stargazers_count"),"license_spdx_id":lic.get("spdx_id"),"license_name":lic.get("name"),"licence_review_status":"needs_human_review","collection_source":"github_search_api"})
  except requests.RequestException as e:print("[WARN]",lang,e)
  time.sleep(2)
 write(DATA/"metadata/repositories.jsonl",rows);print("Repositories:",len(rows))
if __name__=="__main__":main()

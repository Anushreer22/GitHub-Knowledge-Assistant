from .common import DATA,read
def main():
 chunks=read(DATA/"processed/code_chunks.jsonl");qas=read(DATA/"qa/qa_candidates.jsonl");ids=[c.get("chunk_id") for c in chunks];errors=[]
 if len(ids)!=len(set(ids)):errors.append("duplicate chunk IDs")
 known=set(ids)
 for i,c in enumerate(chunks):
  for k in ["repo_id","commit_sha","file_path","language","chunk_id","chunk_type","chunk_name","code_text","start_line","end_line","imports","symbols_defined","symbols_used","parser_status"]:
   if k not in c:errors.append(f"chunk {i} missing {k}")
  if c.get("language") not in {"python","java"}:errors.append(f"chunk {i} invalid language")
  if not isinstance(c.get("start_line"),int) or not isinstance(c.get("end_line"),int) or c["start_line"]<1 or c["end_line"]<c["start_line"]:errors.append(f"chunk {i} bad line range")
 for i,q in enumerate(qas):
  if any(x not in known for x in q.get("relevant_chunk_ids",[])):errors.append(f"QA {i} unknown chunk reference")
 print("chunks",len(chunks),"QA",len(qas),"errors",len(errors))
 for e in errors[:50]:print("ERROR:",e)
 if errors:raise SystemExit(1)
 print("Structural checks passed; semantic labels and licences still require human review.")
if __name__=="__main__":main()

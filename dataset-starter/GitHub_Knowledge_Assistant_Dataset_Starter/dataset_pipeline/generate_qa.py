from .common import DATA,read,write,sid
def main():
 rows=[]
 for c in read(DATA/"processed/code_chunks.jsonl"):
  typ=c["chunk_type"].lower();name=c["chunk_name"]
  if "class" in typ: q=f"Where is the {name} class defined?"
  elif "method" in typ: q=f"Where is the {name} method implemented?"
  elif "function" in typ: q=f"Where is the {name} function implemented?"
  else:q=f"What code is contained in {c['file_path']}?"
  rows.append({"schema_version":"1.0","question_id":"q_"+sid(c["chunk_id"],q),"repo_id":c["repo_id"],"question":q,"expected_answer":None,"relevant_chunk_ids":[c["chunk_id"]],"relevant_files":[c["file_path"]],"difficulty":"single_chunk_candidate","answerable":True,"generation_method":"symbol_template","review_status":"needs_review","reviewer_notes":"","source_chunk_id":c["chunk_id"],"split":None})
 write(DATA/"qa/qa_candidates.jsonl",rows);write(DATA/"qa/qa_review_template.jsonl",rows);print("QA candidates:",len(rows))
if __name__=="__main__":main()

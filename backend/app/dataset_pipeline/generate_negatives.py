import random
from collections import defaultdict
from .common import DATA,read,write,sid
def main():
 chunks=read(DATA/"processed/code_chunks.jsonl");bylang=defaultdict(list);lookup={c["chunk_id"]:c for c in chunks}
 for c in chunks:bylang[c["language"]].append(c)
 rng=random.Random(42);out=[]
 for q in read(DATA/"qa/qa_candidates.jsonl"):
  pos=q["relevant_chunk_ids"][0];lang=lookup[pos]["language"]
  candidates=[c for c in bylang[lang] if c["chunk_id"]!=pos and c["repo_id"]!=q["repo_id"]]
  if not candidates:continue
  neg=rng.choice(candidates)
  out.append({"pair_id":"n_"+sid(q["question_id"],neg["chunk_id"]),"question_id":q["question_id"],"repo_id":q["repo_id"],"question":q["question"],"positive_chunk_id":pos,"negative_chunk_id":neg["chunk_id"],"negative_code_text":neg["code_text"],"negative_sampling_method":"random_same_language_other_repo","label_status":"candidate_needs_review"})
 write(DATA/"qa/hard_negative_candidates.jsonl",out);print("Negative candidates:",len(out))
if __name__=="__main__":main()

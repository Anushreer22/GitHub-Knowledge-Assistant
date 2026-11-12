# Retrieval Engine Comparison Report (Phase 3)

**Evaluated Queries:** 50  
**Evaluation Split:** `C:\Users\ANUSHREE R\GitHub-Knowledge-Assistant\data\splits\test_qa.jsonl`

---

## 1. Overall Performance Metrics

| Metric | BM25 Lexical | Dense Semantic | Hybrid (RRF) |
|---|---|---|---|
| **Recall@1** | 0.6400 | 0.0000 | **0.5000** |
| **Recall@5** | 0.7400 | 0.0200 | **0.7200** |
| **Recall@10** | 0.7800 | 0.0600 | **0.7400** |
| **MRR** | 0.6887 | 0.0145 | **0.5753** |
| **Precision@5** | 0.1480 | 0.0040 | **0.1440** |

---

## 2. Per-Language MRR Breakdown

| Language | BM25 MRR | Dense MRR | Hybrid MRR |
|---|---|---|---|
| java | 0.6887 | 0.0145 | **0.5753** |

---

## 3. Representative Query Analysis

### Hybrid Hits (Rank 1):
- **Query:** *"Where is the AbstractDBAnnotationValidator class defined?"* -> Target Chunk `466c6475c7c80b0892c4` found at Rank 1
- **Query:** *"Which file contains the implementation of AbstractDBAnnotationValidator?"* -> Target Chunk `466c6475c7c80b0892c4` found at Rank 1
- **Query:** *"Where is the AbstractDBAnnotationValidator constructor implemented?"* -> Target Chunk `aafbbc26bd5d0954591f` found at Rank 1

### Difficult Queries (Low Recall):
- **Query:** *"Where is the get method implemented?"* (Target Chunk `ab20fb7d33e584691589` not in top 10)
- **Query:** *"Which file contains the implementation of get?"* (Target Chunk `ab20fb7d33e584691589` not in top 10)
- **Query:** *"Where is the validate method implemented?"* (Target Chunk `b77368605f01ed55032b` not in top 10)
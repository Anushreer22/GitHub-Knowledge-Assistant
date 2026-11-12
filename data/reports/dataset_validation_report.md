# Dataset Quality and Validation Report

**Validation Status:** ✅ PASS  
**Total Chunks:** 243,411  
**Total QA Candidates:** 2,000  
**Total Negative Candidates:** 2,000  
**Errors:** 0 | **Warnings:** 0

---

## 1. Code Chunks Breakdown

- **Unique Chunk IDs:** 243,411
- **Duplicate Chunks:** 0
- **Empty Code Chunks:** 0
- **Invalid Line Ranges:** 0

### Language Distribution
| Language | Chunks |
|---|---|
| python | 7,466 |
| java | 235,945 |

### Repository Distribution
| Repository ID | Chunks |
|---|---|
| public-apis__public-apis | 59 |
| EbookFoundation__free-programming-books | 6 |
| NationalSecurityAgency__ghidra | 208,244 |
| iluwatar__java-design-patterns | 7,679 |
| pallets__werkzeug | 2,249 |
| bottlepy__bottle | 640 |
| marshmallow-code__marshmallow | 1,668 |
| google__gson | 3,763 |
| square__retrofit | 3,448 |
| cbeust__testng | 15,655 |

---

## 2. QA Candidates Integrity

- **Total Generated QA:** 2,000
- **Unique Questions:** 2,000
- **Missing Chunk References:** 0
- **Missing Answers (Answerable=True):** 0

### Review Statuses
| Review Status | Count |
|---|---|
| pending | 2,000 |

---

## 3. Negative Sampling Verification

- **Total Negative Pairs:** 2,000
- **Unique Pairs:** 2,000
- **Invalid Negative References:** 0
- **False Negative Risks (Pos == Neg):** 0

---

## 4. Repository Split & Leakage Verification

- **Train Repositories (8):** bottlepy__bottle, cbeust__testng, google__gson, iluwatar__java-design-patterns, marshmallow-code__marshmallow, pallets__werkzeug, public-apis__public-apis, square__retrofit
- **Validation Repositories (1):** EbookFoundation__free-programming-books
- **Test Repositories (1):** NationalSecurityAgency__ghidra
- **Leakage Detected:** None (Clean Disjoint Sets)

---

## 5. Structural vs Semantic Human Review

> [!IMPORTANT]
> Structural validation checks schema, references, line ranges, and leakage. Semantic accuracy and license compliance require human review.
> Pending Human Review: **2,000** | Approved: **0** | Rejected: **0**

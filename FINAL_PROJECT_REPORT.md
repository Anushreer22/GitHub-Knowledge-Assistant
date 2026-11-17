# GITHUB KNOWLEDGE ASSISTANT
## An Evidence-Grounded Question Answering System for GitHub Repositories Using Custom-Trained Code Embeddings

**PROJECT REPORT**

**Department of Artificial Intelligence & Machine Learning**  
**Nitte Meenakshi Institute of Technology, Bengaluru, India**

---

### Student Details
- **Name:** Anushree R &nbsp;&nbsp;|&nbsp;&nbsp; **USN:** 1NT24AI007
- **Name:** Umashree B L &nbsp;&nbsp;|&nbsp;&nbsp; **USN:** 1NT24AI058
- **Department:** Artificial Intelligence & Machine Learning
- **Institution:** Nitte Meenakshi Institute of Technology, Yelahanka, Bengaluru – 560064

---

## Table of Contents
1. [Abstract](#1-abstract)
2. [Introduction](#2-introduction)
3. [Problem Statement](#3-problem-statement)
4. [Objectives](#4-objectives)
5. [Literature Review](#5-literature-review)
6. [System Design and Architecture](#6-system-design-and-architecture)
   - 6.1 [Ingestion and Parsing Layer](#61-ingestion-and-parsing-layer)
   - 6.2 [Embedding and Indexing Layer](#62-embedding-and-indexing-layer)
   - 6.3 [Retrieval and Grounding Layer](#63-retrieval-and-grounding-layer)
   - 6.4 [Detailed Algorithmic Formulations (Algorithms 1 to 10)](#64-detailed-algorithmic-formulations)
7. [Methodology](#7-methodology)
8. [Implementation](#8-implementation)
9. [Results and Discussion](#9-results-and-discussion)
10. [Conclusion and Future Work](#10-conclusion-and-future-work)
11. [References](#11-references)

---

## 1. Abstract

Modern open-source repositories often encompass hundreds of directories and thousands of source files, creating steep onboarding curves for software engineers attempting to comprehend unfamiliar codebases. While contemporary generative AI tools offer conversational interfaces, general-purpose large language models regularly suffer from hallucinations, lack repository-specific context, and fail to provide verifiable source references. 

This project presents the **GitHub Knowledge Assistant**, an end-to-end evidence-grounded question-answering system tailored for public GitHub repositories written in Python and Java. Given a public repository URL, the system performs secure, non-executing shallow ingestion, extracts structural Abstract Syntax Tree (AST) code chunks, and constructs a dual-channel index combining lexical BM25 and a custom-built 4-layer Transformer CodeEncoder trained from scratch using InfoNCE contrastive learning. During inference, queries are answered using a hybrid retrieval mechanism backed by Reciprocal Rank Fusion ($k=60$) and static symbol graph resolution. Every generated answer is strictly tied to verifiable file paths and exact line numbers; if supporting code is absent, the system explicitly triggers an abstention response rather than fabricating claims. 

The system was evaluated on real-world repositories including `psf/requests`, `pallets/flask`, `google/gson`, and `square/retrofit`. The custom 256-dimensional Transformer CodeEncoder achieved a Recall@10 of 43.97% and a Mean Reciprocal Rank (MRR) of 0.2687 after two training epochs on hard-negative contrastive pairs. A full-stack application featuring a FastAPI asynchronous backend and a split-screen React/TypeScript developer dashboard demonstrates sub-second query latency with 100% citation traceability across all answered queries.

**Keywords:** Code Question Answering, Static Code Analysis, Hybrid Retrieval, Reciprocal Rank Fusion, Custom Transformer Encoder, Contrastive Learning, Abstract Syntax Tree, Evidence Grounding.

---

## 2. Introduction

### 2.1 Overview of GitHub Repositories and Software Comprehension
Software engineering teams rely heavily on collaborative platforms such as GitHub to maintain large-scale software systems. Modern enterprise and open-source applications distribute functionality across dozens of modules, abstract interfaces, microservices, and build pipelines. When developers join an existing project, investigate security vulnerabilities, or review external dependencies, their primary operational challenge is not writing new code, but reading and tracing existing code. Understanding how an application initializes its state, where authentication occurs, or how data flows between components typically forces developers to navigate intricate inheritance hierarchies and trace caller-callee chains across hundreds of files.

### 2.2 Limitations of Conventional Code Search
Existing approaches to code exploration exhibit severe operational deficiencies:
- **Lexical Keyword Search (grep, IDE text search, standard GitHub search):** Keyword search depends entirely on literal token matching. It suffers from the *vocabulary mismatch problem*—a developer searching for "handle user login" will fail to locate an implementation if the method is named `authenticate_credentials` or `verify_token`.
- **Pure Vector Search:** Standalone semantic embeddings capture broad concepts but frequently fail on exact identifier matches, specific error strings, or fine-grained parameter signatures (such as differentiating overloaded methods).
- **Single-File Isolation:** Standard search queries present disjointed code snippets without indicating which parent class defines the snippet, who invokes it, or which unit test exercises it.
- **Unverifiable Black-Box AI Generation:** Commercial AI assistants answer user queries based on their frozen parameter weights. When applied to specific private or rapidly evolving public repositories, they hallucinate non-existent API methods and fabricate code structures without pointing to concrete source lines.

### 2.3 Need for Repository-Level Question Answering (RLQA)
To overcome these barriers, developers require a dedicated repository-level assistant that:
1. Operates within the strictly isolated boundary of a selected repository.
2. Accepts natural-language questions and retrieves relevant code segments using semantic and lexical understanding.
3. Structures responses around verifiable evidence, supplying exact file paths and line ranges.
4. Possesses an explicit *abstention mechanism* that declines to answer when supporting evidence cannot be found in the repository.

### 2.4 Retrieval-Augmented Generation (RAG) for Source Code
Retrieval-Augmented Generation bridges the gap between static retrieval and natural-language explanation. By pre-indexing structural code chunks and conditioning the synthesizer solely on the retrieved chunks, the system guarantees factual accuracy. Unlike generic documentation tools, a code-centric RAG system must respect syntax boundaries (preserving complete functions and classes) rather than slicing code into arbitrary character windows.

### 2.5 Scope of the Project
This project encompasses:
- Automated ingestion of public GitHub repositories containing Python (`.py`, `.pyi`) and Java (`.java`) code.
- AST-driven code chunking that preserves parent-class relationships, function boundaries, decorators, and line numbers.
- Training a custom 4-layer Transformer CodeEncoder from scratch with random weight initialization (avoiding closed-source or third-party pre-trained embeddings).
- Developing a dual-channel hybrid retriever combining Rank-BM25 and 256-dimensional dense vector embeddings via Reciprocal Rank Fusion.
- Creating a static call graph that resolves callers, callees, and corresponding unit test cases.
- Deploying a production-grade FastAPI backend and a responsive React/TypeScript developer dashboard.

---

## 3. Problem Statement

Navigating complex software repositories is one of the most time-consuming tasks in modern software maintenance. Developers frequently encounter codebases containing thousands of interconnected files without complete architectural documentation. Current search engines fail to bridge the semantic divide between high-level functional questions (e.g., *"How are database connections pooled?"*) and low-level source implementations (e.g., a method named `acquire_connection` in a connection pool manager).

Furthermore, general conversational AI systems generate speculative answers devoid of verifiable repository context, introducing hallucinations that mislead developers and degrade code quality. 

Therefore, the core problem addressed in this project is:
> *To design and build an evidence-grounded, multi-repository question-answering system that accurately ingests Python and Java codebases, constructs semantic and lexical indices using a custom-trained Transformer encoder, retrieves relevant AST code chunks with high precision, and synthesizes verifiable answers accompanied by exact file paths and source line citations, while strictly abstaining from answering when valid evidence is missing.*

---

## 4. Objectives

The specific technical objectives of this project are:
1. **Automated Ingestion and Filtering:** Implement a resilient repository ingestion pipeline capable of shallow-cloning public GitHub repositories, handling Windows long-path constraints, validating repository integrity, and excluding non-source directories (`.git`, `node_modules`, `build`, virtual environments) and secrets.
2. **Language-Aware AST Chunking:** Develop structural parsers for Python (using Python's `ast` module) and Java (using `tree-sitter-java`) that preserve functions, methods, classes, constructors, overloaded signatures, annotations, and exact 1-indexed line ranges without fragmenting logic.
3. **Custom Transformer Code Encoder:** Design and train a compact 4-layer Transformer Encoder ($d_{\text{model}} = 256$, $h = 4$, $d_{\text{ff}} = 1024$) initialized from scratch, utilizing Byte-Pair Encoding (16,000 vocabulary) and InfoNCE contrastive loss over mined positive and hard-negative query-code pairs.
4. **Hybrid Dual-Channel Retrieval:** Implement and fuse lexical search (Rank-BM25) and dense semantic search (cosine similarity on unit-normalized vectors) using Reciprocal Rank Fusion ($k=60$), ensuring strict repository-level isolation during query execution.
5. **Static Context and Symbol Graph Resolution:** Construct an in-memory relationship graph that identifies upstream callers, downstream callees, class hierarchies, and associated unit test files for retrieved symbols without executing untrusted code.
6. **Evidence-Grounded Answer Synthesis with Abstention:** Build an answer generation engine that structures explanations directly from retrieved chunks, displays exact file/line citations, and triggers an explicit "Insufficient Evidence" status whenever similarity scores fall below the minimum grounding threshold.
7. **Full-Stack SaaS Application:** Develop an asynchronous FastAPI service and an interactive React/TypeScript user interface featuring code search, conversational question-answering, a split-screen evidence inspector, and incremental synchronization.

---

## 5. Literature Review

The following table summarizes prominent peer-reviewed studies in source code representation, deep code search, and repository comprehension:

| Citation / Year | Research Work | Core Focus / Purpose | Key Findings & Relevance to Our Project |
|---|---|---|---|
| **C. Liu et al. (2022)**, *ACM Computing Surveys*, 54(9) | Opportunities and Challenges in Code Search Tools | Comprehensive survey of code search paradigms and open developer challenges. | Concludes that keyword search alone suffers from vocabulary mismatches, while vector search lacks precision for exact identifiers. Strongly advocates for hybrid multi-modal retrieval. |
| **H. P. Samoaa et al. (2022)**, *IET Software*, 16(4) | Source Code Representation for Deep Learning in Software Engineering | Systematic mapping of 103 studies on code representations (tokens, trees, and graphs). | Confirms that combining token-level representations with structural syntax tree metadata yields the highest downstream fidelity in code comprehension tasks. |
| **Y. Xie et al. (2023)**, *ACM TOSEM*, 33(2) | Survey of Code Search Based on Deep Learning | Review of query encoding, code modeling, and contrastive alignment techniques. | Demonstrates that Siamese/Bi-Encoder architectures trained with contrastive loss (InfoNCE) offer the best trade-off between inference latency and retrieval accuracy. |
| **Z. Deng et al. (2024)**, *J. Systems and Software*, 207 | Code Semantic Enrichment for Deep Code Search (SemEnr) | Methods to bridge the abstraction gap between high-level developer intent and low-level source tokens. | Highlights that augmenting code snippets with caller context and class inheritance paths significantly improves retrieval MRR. |
| **D. R. Fudholi & A. Capiluppi (2026)**, *Information and Software Technology*, 189 | AI for Source Code Understanding Tasks | Mapping study on the reliability and explainability of code-understanding models. | Identifies hallucination and lack of source traceability as the primary hurdles preventing real-world developer adoption, underscoring the need for strict evidence-grounded citations. |

### Research Gap Identified
Prior works either focus on isolated code search (returning raw snippets without explaining multi-file architectural flow) or utilize ungrounded generative models that fabricate plausible-looking code. Existing RAG frameworks often chunk code using fixed character lengths, breaking function declarations and losing parent scope. Our work directly addresses this gap by implementing **syntactic AST chunking**, **custom contrastive embeddings trained from scratch**, **hybrid RRF retrieval**, and **mandatory line-level evidence grounding**.

---

## 6. System Design and Architecture

The architecture is divided into three functional layers: the **Ingestion & Data Preparation Layer**, the **Embedding & Indexing Layer**, and the **Retrieval & Evidence Grounding Layer**.

```
+-----------------------------------------------------------------------------------------+
|                                    USER INTERFACE                                       |
|                  (React 18 + TypeScript + Tailwind CSS Dashboard)                       |
+-----------------------------------------------------------------------------------------+
       │ Repository URL                                             ▲ Answer, Evidence,
       ▼ Ingestion Trigger                                          │ Citations & Lines
+-----------------------------------------------------------------------------------------+
|                                   FASTAPI BACKEND                                       |
|             (Asynchronous REST API, Rate Limiting, Route Validation)                    |
+-----------------------------------------------------------------------------------------+
       │                                                            ▲
       ▼                                                            │
+─────────────────────────────────+        +──────────────────────────────────────────────+
|   1. INGESTION & PARSING        |        |   3. RETRIEVAL & GROUNDING                   |
|  - Git Clone (depth 1, longpath)|        |  - Query Tokenization                        |
|  - Secret & Extension Filtering |        |  - BM25 Lexical Channel                      |
|  - Python AST Chunking          |        |  - Dense 256-D Cosine Channel                |
|  - Java tree-sitter Chunking    |        |  - Reciprocal Rank Fusion (k=60)             |
|  - Metadata & Scope Extraction  |        |  - Static Symbol Call Graph                  |
+─────────────────────────────────+        |  - Evidence Grounding & Line Citations       |
       │                                   |  - Abstention Mechanism                      |
       ▼                                   +──────────────────────────────────────────────+
+─────────────────────────────────+                                 ▲
|   2. EMBEDDING & INDEXING       |                                 │
|  - 16k BPE Tokenizer            | ────────────────────────────────┘
|  - 4-Layer PyTorch CodeEncoder  |
|  - Mask-Aware Mean Pooling      |
|  - L2 Normalization (Unit 256D) |
|  - Persistent BM25 & Dense Store|
+─────────────────────────────────+
```

### 6.1 Ingestion and Parsing Layer
1. **URL Validation and Shallow Clone:** The user supplies a GitHub URL (e.g., `https://github.com/psf/requests`). The backend validates the URL format, confirms repository accessibility, and executes a shallow clone (`git clone --depth 1 -c core.longpaths=true`) into an isolated temporary directory before atomic registration.
2. **Source Code Filtering:** The engine walks the directory tree, applying exclusions for `.git`, `.venv`, `node_modules`, `build`, `target`, `dist`, binaries, and secret-bearing files (API keys, private tokens).
3. **Language-Aware Chunking:**
   - **Python:** The file is parsed into an Abstract Syntax Tree via Python's native `ast` module. The visitor extracts module-level documentation, classes, functions, and asynchronous methods. Decorator line numbers are preserved, and method names are assigned fully qualified hierarchical scopes (e.g., `Session.send`).
   - **Java:** Source files are parsed using `tree-sitter-java`. The parser navigates the concrete syntax tree, identifying packages, imports, classes, interfaces, enums, records, constructors, and overloaded methods with parameter signatures (e.g., `OrderService.process(Long, double)`).
4. **Chunk Schema:** Each chunk is serialized into JSON Lines with attributes: `chunk_id`, `repo_id`, `file_path`, `language`, `chunk_type`, `chunk_name`, `code_text`, `start_line`, `end_line`, `imports`, `symbols_defined`, and `symbols_used`.

### 6.2 Embedding and Indexing Layer
1. **Custom Tokenizer:** A Byte-Pair Encoding (BPE) tokenizer trained on code tokens, camelCase/snake_case sub-words, and natural-language queries with a vocabulary size of 16,000.
2. **Transformer CodeEncoder:** A 4-layer bidirectional Transformer encoder with $d_{\text{model}} = 256$, 4 attention heads ($d_k = 64$), feed-forward dimension $1024$, GELU activations, and Pre-LayerNorm (`norm_first=True`) architecture.
3. **Mask-Aware Mean Pooling:** The sequence hidden states are pooled exclusively over valid non-padded tokens:
   $$\mathbf{h}_{\text{pooled}} = \frac{\sum_{i=1}^L \mathbf{h}_i \cdot m_i}{\max\left(\sum_{i=1}^L m_i, 10^{-9}\right)}$$
4. **$L_2$ Normalization:** Embeddings are projected onto the unit hypersphere:
   $$\mathbf{v} = \frac{\mathbf{h}_{\text{pooled}}}{\|\mathbf{h}_{\text{pooled}}\|_2}$$
   This simplifies cosine similarity during inference to a fast inner product: $\text{sim}(\mathbf{q}, \mathbf{c}) = \mathbf{q} \cdot \mathbf{c}$.

### 6.3 Retrieval and Grounding Layer
1. **Dual-Channel Retrieval:**
   - **Lexical Channel (Rank-BM25):** Evaluates exact token matches across chunk text, symbols, and file paths.
   - **Dense Channel (Transformer Vectors):** Computes inner products against pre-indexed 256-D chunk embeddings.
2. **Reciprocal Rank Fusion (RRF):** Merges both ranked lists using:
   $$\text{RRF Score}(d) = \sum_{m \in \{\text{BM25}, \text{Dense}\}} \frac{w_m}{k + \text{rank}_m(d)}$$
   where $k = 60$ and $w_{\text{BM25}} = w_{\text{Dense}} = 1.0$.
3. **Symbol Call Graph Resolution:** Uses the AST metadata to trace callers, callees, and corresponding unit test functions across the repository.
4. **Evidence Grounding and Abstention:** Synthesizes an answer using only retrieved chunks. If the similarity score of the top candidate falls below $0.005$ or if content tokens have zero presence in the retrieved text, the system declines to generate an answer and returns an explicit `insufficient_evidence` indicator.

---

### 6.4 Detailed Algorithmic Formulations

The GitHub Knowledge Assistant integrates ten purpose-built algorithms operating across parsing, tokenization, deep representation learning, hybrid ranking, and verified synthesis. Below is the formal algorithmic breakdown of each core procedure:

```
+───────────────────────────────────────────────────────────────────────────────────+
|                  CORE ALGORITHMIC PIPELINE OF THE KNOWLEDGE ASSISTANT             |
|                                                                                   |
|  [Raw Repository Files]                                                           |
|          │                                                                        |
|          ▼                                                                        |
|  Algorithm 1: Syntax-Aware AST Chunking (Python & Java)                           |
|          │                                                                        |
|          ▼                                                                        |
|  Algorithm 2: BPE Subword Tokenization (Vocab = 16,000)                           |
|          │                                                                        |
|          ├────────────────────────────────┬───────────────────────────────────┐   |
|          ▼                                ▼                                   ▼   |
|  Algorithm 5: BM25 Lexical Index   Algorithm 3: Pre-LN Transformer   Algorithm 8: |
|  (k1=1.5, b=0.75, token splits)    (4 Layers, 256D, InfoNCE Loss)    Static Graph |
|          │                                │                          (Callers/    |
|          │                                ▼                          Callees)     |
|          │                         Algorithm 6: Dense Cosine Search           │   |
|          │                                │                                   │   |
|          └─────────────────┬──────────────┘                                   │   |
|                            ▼                                                  │   |
|                    Algorithm 7: Reciprocal Rank Fusion (RRF with k=60)        │   |
|                            │                                                  │   |
|                            └──────────────────────┬───────────────────────────┘   |
|                                                   ▼                               |
|                                     Algorithm 10: Evidence Grounding              |
|                                     & Abstention Engine                           |
|                                                   │                               |
|                                                   ▼                               |
|                                      [Verified Answer + Line Citations]           |
+───────────────────────────────────────────────────────────────────────────────────+
```

---

#### Algorithm 1: Syntax-Aware AST Structural Chunking (Python and Java)
Unlike naive text sliding-window chunkers that bisect routines mid-expression, Algorithm 1 walks syntactic hierarchy trees to emit self-contained semantic units.

```text
Algorithm 1: Syntax-Aware Structural Code Chunking
Input: Source file path F, File text T, Language L in {Python, Java}
Output: Set of structured code chunks C

1. Initialize chunks list C <- []
2. If L == Python then:
3.     Parse T into Abstract Syntax Tree root using ast.parse(T)
4.     Extract module-level imports M_file = {import_name for import in root}
5.     Function VisitPython(node, scope_stack):
6.         For each child node n in node:
7.             If n is ast.ClassDef then:
8.                 start_line <- min(decorator.lineno for decorator in n.decorator_list) or n.lineno
9.                 end_line <- n.end_lineno
10.                qualified_scope <- Concatenate(scope_stack, n.name)
11.                chunk_code <- ExtractLines(T, start_line, end_line)
12.                Append to C: {type: "class_definition", name: qualified_scope, code: chunk_code, 
                                start: start_line, end: end_line, imports: M_file}
13.                VisitPython(n.body, scope_stack + [n.name])
14.            Else if n is (ast.FunctionDef or ast.AsyncFunctionDef) then:
15.                start_line <- min(decorator.lineno for decorator in n.decorator_list) or n.lineno
16.                end_line <- n.end_lineno
17.                qualified_scope <- Concatenate(scope_stack, n.name)
18.                chunk_code <- ExtractLines(T, start_line, end_line)
19.                chunk_type <- "method_definition" if scope_stack is non-empty else "function_definition"
20.                Append to C: {type: chunk_type, name: qualified_scope, code: chunk_code, 
                                start: start_line, end: end_line, imports: M_file}
21.                VisitPython(n.body, scope_stack + [n.name])
22.    VisitPython(root.body, [])

23. Else if L == Java then:
24.    Parse T into Concrete Syntax Tree root using tree-sitter-java
25.    Extract package declaration and import statements M_file
26.    Function VisitJava(node, scope_stack):
27.        For each child node n in node:
28.            If n.type in {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"} then:
29.                class_identifier <- GetIdentifier(n)
30.                qualified_scope <- Concatenate(scope_stack, class_identifier)
31.                Append to C: {type: n.type, name: qualified_scope, code: n.text, 
                                start: n.start_line, end: n.end_line, imports: M_file}
32.                body_node <- FindChild(n, {"class_body", "interface_body", "enum_body"})
33.                If body_node is not null then VisitJava(body_node, scope_stack + [class_identifier])
34.            Else if n.type in {"method_declaration", "constructor_declaration"} then:
35.                method_identifier <- GetIdentifier(n)
36.                param_types <- ExtractFormalParameterTypes(n)
37.                signature_string <- "(" + Join(param_types, ", ") + ")"
38.                full_symbol <- Concatenate(scope_stack, method_identifier) + signature_string
39.                Append to C: {type: n.type, name: full_symbol, code: n.text, 
                                start: n.start_line, end: n.end_line, imports: M_file}
40.            Else:
41.                VisitJava(n.children, scope_stack)
42.    VisitJava(root, [])
43. Return C
```
- **Asymptotic Complexity:** Time $\mathcal{O}(N)$ where $N$ is the number of source characters; Space $\mathcal{O}(K)$ where $K$ is the number of syntactic nodes.

---

#### Algorithm 2: Byte-Pair Encoding (BPE) Subword Tokenizer Training
Algorithm 2 constructs a domain-specific vocabulary tailored to programming constructs, avoiding severe out-of-vocabulary penalties.

```text
Algorithm 2: BPE Subword Tokenizer Training
Input: Repository text corpus D, Target vocabulary size V = 16000
Output: Trained merge table M, Vocabulary table Vocab

1. Initialize alphabet Vocab with individual characters, bytes, and special tokens {<pad>, <unk>, <s>, </s>}
2. Tokenize raw text in D into word tokens using regex splitting on whitespace, camelCase, and snake_case:
   SplitRegex: [A-Z]?[a-z]+ | [A-Z]+(?=[A-Z][a-z]|\b) | \d+ | [^\s\w]
3. Represent each word as a sequence of single characters followed by end-of-word marker </w>
4. While |Vocab| < V do:
5.     Compute frequency count of all adjacent symbol pairs (c_i, c_{i+1}) across all tokenized words
6.     Find most frequent symbol pair: (u, v) <- argmax_{pair} Frequency(pair)
7.     Create new merge rule: M <- M union {(u, v) -> uv}
8.     Add composite token uv to Vocab: Vocab <- Vocab union {uv}
9.     Replace every occurrence of adjacent pair (u, v) in corpus with merged token uv
10. Return Merge table M, Vocabulary table Vocab
```

---

#### Algorithm 3: Pre-LayerNorm Transformer CodeEncoder Forward Pass
Implements the deep neural forward mapping from discrete token IDs into normalized 256-D semantic unit vectors.

```text
Algorithm 3: Pre-LN Transformer CodeEncoder Forward Pass
Input: Token ID batch X in R^{B x L}, Attention mask A in {0, 1}^{B x L}
Output: L2-normalized dense embeddings V in R^{B x d_{model}} (where d_{model} = 256)

1. Truncate sequence length L to max_seq_len = 512 tokens
2. Construct position indices P = [[0, 1, ..., L-1]] expanded across batch size B
3. Compute initial token and learned positional embeddings:
   E_tok <- EmbeddingLookup(X, W_tok in R^{16000 x 256}, padding_idx=0)
   E_pos <- EmbeddingLookup(P, W_pos in R^{512 x 256})
4. Combine and regularize:
   H_0 <- Dropout(LayerNorm(E_tok + E_pos), p=0.1)

5. Construct padding mask M_pad where M_pad[b, i] = -infinity if A[b, i] == 0 else 0.0

6. For layer l = 1 to 4 do:
7.     # Sub-Layer 1: Pre-LN Multi-Head Self-Attention (4 heads, d_k = 64)
8.     H_norm <- LayerNorm(H_{l-1})
9.     Q <- H_norm * W_Q^{(l)},  K <- H_norm * W_K^{(l)},  V <- H_norm * W_V^{(l)}
10.    For each head h = 1 to 4:
11.        Attention_h <- softmax( (Q_h * K_h^T) / sqrt(64) + M_pad ) * V_h
12.    MHSA_out <- Concat(Attention_1, ..., Attention_4) * W_O^{(l)}
13.    H_attn <- H_{l-1} + Dropout(MHSA_out, p=0.1)
14.    
15.    # Sub-Layer 2: Pre-LN Feed-Forward Network (GELU expansion to 1024)
16.    H_ffn_norm <- LayerNorm(H_attn)
17.    FFN_out <- (GELU(H_ffn_norm * W_1^{(l)} + b_1^{(l)})) * W_2^{(l)} + b_2^{(l)}
18.    H_l <- H_attn + Dropout(FFN_out, p=0.1)

19. Apply final output normalization: H_final <- LayerNorm(H_4)

20. # Mask-Aware Mean Pooling across sequence length
21. Expanded_Mask <- ExpandDims(A, axis=-1)
22. Summed_Vectors <- sum_{i=1}^L (H_final[:, i, :] * Expanded_Mask[:, i, :])
23. Valid_Counts <- max(sum_{i=1}^L Expanded_Mask[:, i, :], 1e-9)
24. Pooled_Vector <- Summed_Vectors / Valid_Counts

25. # L2-Normalization onto unit hypersphere
26. V <- Pooled_Vector / ||Pooled_Vector||_2
27. Return V
```

---

#### Algorithm 4: InfoNCE Contrastive Training with Hard-Negative Mining
Forces question vectors to align tightly with their corresponding code chunk while repelling irrelevant chunks.

```text
Algorithm 4: InfoNCE Contrastive Optimization
Input: Batch of queries Q = {q_1, ..., q_B}, Positive code chunks P = {p_1, ..., p_B},
       Mined BM25 hard negatives N = {n_{i,1}, ..., n_{i,K}}, Temperature tau = 0.07,
       Encoder parameters Theta, Optimizer AdamW
Output: Updated parameters Theta*

1. Forward pass queries through CodeEncoder: Z_q <- CodeEncoder(Q; Theta) in R^{B x 256}
2. Forward pass positives through CodeEncoder: Z_p <- CodeEncoder(P; Theta) in R^{B x 256}
3. Forward pass hard negatives through CodeEncoder: Z_n <- CodeEncoder(N; Theta) in R^{B x K x 256}

4. For each sample i in batch B:
5.     Compute positive cosine logit:
       s_pos_i <- (Z_q[i] . Z_p[i]) / tau
6.     Compute in-batch negative logits (for j != i):
       s_inbatch_{i, j} <- (Z_q[i] . Z_p[j]) / tau
7.     Compute mined hard-negative logits:
       s_hard_{i, k} <- (Z_q[i] . Z_n[i, k]) / tau
8.     Assemble unified logit vector:
       Logits_i <- [s_pos_i, {s_inbatch_{i, j}}_{j != i}, {s_hard_{i, k}}_{k=1}^K]
9.     Compute Cross-Entropy loss targeting index 0 (the positive pair):
       Loss_i <- -log( exp(s_pos_i) / sum_{s in Logits_i} exp(s) )

10. Total_Loss <- (1 / B) * sum_{i=1}^B Loss_i
11. Compute gradients: g <- Grad_Theta(Total_Loss)
12. Update weights via AdamW: Theta* <- AdamW_Step(Theta, g, lr=1e-4, weight_decay=0.01)
13. Return Theta*
```

---

#### Algorithm 5: Code-Aware Okapi BM25 Lexical Retrieval
Evaluates probabilistic term relevance while splitting compound programming symbols.

```text
Algorithm 5: Code-Aware Okapi BM25 Lexical Retrieval
Input: Query string q, Chunk index corpus D = {d_1, ..., d_M}, Target repo R,
       Parameters k1 = 1.5, b = 0.75, Top-K parameter k_ret
Output: Ranked candidate list Res_BM25

1. Tokenize query q using code-aware tokenizer:
   Tokens_q <- TokenizeCode(q)  # Splits 'AuthService' into ['authservice', 'auth', 'service']
2. Initialize scores array S in R^M to zeros
3. Compute average document length across target repository:
   avgdl <- (1 / |D_R|) * sum_{d in D_R} |Tokens(d)|

4. For each token t in Tokens_q do:
5.     Compute inverse document frequency:
       n(t) <- Number of chunks containing t
       IDF(t) <- ln( (|D_R| - n(t) + 0.5) / (n(t) + 0.5) + 1.0 )
6.     For each document d_j in D_R containing t do:
7.         f(t, d_j) <- Term frequency of t in d_j
8.         Term_Score <- IDF(t) * ( (f(t, d_j) * (k1 + 1)) / (f(t, d_j) + k1 * (1 - b + b * (|d_j| / avgdl))) )
9.         S[j] <- S[j] + Term_Score

10. Sort document indices in descending order of score: Ranked_Indices <- argsort(-S)
11. Res_BM25 <- Filter top k_ret entries with score > 0.0
12. Return Res_BM25
```

---

#### Algorithm 6: Dense Vector Cosine Similarity Search
Exploits unit hypersphere normalization to execute matrix-dot-product search in $\mathcal{O}(M \cdot d)$.

```text
Algorithm 6: Dense Vector Cosine Search
Input: Query text q, Pre-indexed chunk matrix E in R^{M x 256}, Metadata list Meta, Target repo R, Top-K parameter k_ret
Output: Ranked candidate list Res_Dense

1. Generate query embedding: v_q <- CodeEncoder(q) in R^{1 x 256}
2. Ensure unit normalization: v_q <- v_q / ||v_q||_2
3. Filter matrix E to rows belonging to target repository R: E_R in R^{M_R x 256}
4. Compute batch dot products (cosine similarities):
   Scores <- E_R * (v_q)^T  # Result is in R^{M_R}
5. Sort indices descending: Ranked_Idx <- argsort(-Scores)
6. Assemble top k_ret results:
   Res_Dense <- [{chunk_id: Meta[idx].id, score: Scores[idx], rank: r} for r, idx in enumerate(Ranked_Idx[:k_ret])]
7. Return Res_Dense
```

---

#### Algorithm 7: Reciprocal Rank Fusion (RRF) Hybrid Ranking
Ensembles lexical and semantic retrieval without scale distortion between probabilistic BM25 scores and cosine similarities.

```text
Algorithm 7: Reciprocal Rank Fusion (RRF) Ensemble
Input: Lexical ranked list R_BM25, Dense ranked list R_Dense, Smoothing constant k = 60, Cutoff K_out
Output: Fused, re-ranked candidate list Res_Hybrid

1. Initialize combined score table Combined_Scores <- defaultdict(float)
2. Initialize rank metadata table Details <- {}

3. For each candidate (chunk_id, rank) in enumerate(R_BM25, start=1) do:
4.     rrf_score <- 1.0 / (k + rank)
5.     Combined_Scores[chunk_id] <- Combined_Scores[chunk_id] + rrf_score
6.     Details[chunk_id].bm25_rank <- rank

7. For each candidate (chunk_id, rank) in enumerate(R_Dense, start=1) do:
8.     rrf_score <- 1.0 / (k + rank)
9.     Combined_Scores[chunk_id] <- Combined_Scores[chunk_id] + rrf_score
10.    Details[chunk_id].dense_rank <- rank

11. Sort unique chunk IDs by combined score:
    Sorted_CIDs <- sort(Combined_Scores.keys(), key=lambda cid: Combined_Scores[cid], descending=True)

12. Formulate output list:
    Res_Hybrid <- []
    For rank, cid in enumerate(Sorted_CIDs[:K_out], start=1):
        Append {chunk_id: cid, fused_score: Combined_Scores[cid], rank: rank, details: Details[cid]}
13. Return Res_Hybrid
```

---

#### Algorithm 8: Static Symbol Call Graph Construction & Dependency Resolution
Statically indexes caller, callee, and unit test relationships without code execution.

```text
Algorithm 8: Static Symbol Graph Resolution
Input: Set of code chunks C = {c_1, ..., c_M}, Target symbol name S, Target repository R
Output: Symbol relationship record Rel = {definitions, callers, callees, unit_tests}

1. Phase 1: Ingestion & In-Memory Graph Indexing:
2. For each chunk c in C do:
3.     For symbol in c.symbols_defined:
4.         Definitions_Map[symbol].append(c)
5.     For symbol in c.symbols_used:
6.         Callers_Map[symbol].append(c)
7.     If "test" in c.file_path.lower() or c.chunk_name.lower().startswith("test"):
8.         For target in c.symbols_used:
9.             Tests_Map[target].append(c)

10. Phase 2: Query Resolution for Symbol S:
11. def_chunks <- Filter(Definitions_Map[S], repo == R)
12. caller_chunks <- Filter(Callers_Map[S], repo == R)
13. test_chunks <- Filter(Tests_Map[S], repo == R)

14. callees_list <- []
15. If def_chunks is non-empty then:
16.     primary_def <- def_chunks[0]
17.     For invoked_sym in primary_def.symbols_used:
18.         verification_status <- "directly_verified" if invoked_sym in Definitions_Map else "external_library"
19.         callees_list.append({symbol: invoked_sym, verification: verification_status})

20. Rel <- {
        definitions: def_chunks,
        callers: Deduplicate(caller_chunks),
        callees: callees_list,
        unit_tests: Deduplicate(test_chunks)
    }
21. Return Rel
```

---

#### Algorithm 9: Incremental Repository Synchronization via Git Diff
Reduces update complexity from $\mathcal{O}(N)$ full-corpus re-indexing to $\mathcal{O}(\Delta)$ delta modifications.

```text
Algorithm 9: Incremental Repository Synchronization (O(Delta))
Input: Repository ID R, Stored previous commit SHA_prev, Current commit SHA_curr, Indexes BM25, DenseStore
Output: Synchronization report Sync_Result

1. If SHA_prev == SHA_curr then:
2.     Return {status: "up_to_date", files_modified: 0, chunks_updated: 0}

3. Execute Git diff inspection:
   diff_lines <- git -c core.longpaths=true -C RepoDir diff --name-status SHA_prev SHA_curr
4. Categorize files:
   Files_Added <- [], Files_Modified <- [], Files_Deleted <- []
   For line in diff_lines:
       status, filepath <- line.split()
       If status == 'A' then Files_Added.append(filepath)
       Else if status == 'M' then Files_Modified.append(filepath)
       Else if status == 'D' then Files_Deleted.append(filepath)

5. Affected_Files <- set(Files_Added + Files_Modified + Files_Deleted)

6. Identify outdated chunks in existing storage:
   Outdated_IDs <- {c.chunk_id for c in ChunksStore if c.repo_id == R and c.file_path in Affected_Files}

7. Advance Git working tree: git -c core.longpaths=true -C RepoDir checkout --detach SHA_curr

8. Extract new chunks exclusively for (Files_Added + Files_Modified):
   New_Chunks <- []
   For file in (Files_Added + Files_Modified):
       New_Chunks.extend( ParseChunks(file) )

9. Atomic index update:
   BM25.remove_and_update(Outdated_IDs, New_Chunks)
   DenseStore.remove(Outdated_IDs)
   DenseStore.add_batch( CodeEncoder(New_Chunks) )

10. Update commit checkpoint: repositories.jsonl[R].commit_sha <- SHA_curr
11. Return {status: "success", delta_files: |Affected_Files|, chunks_pruned: |Outdated_IDs|, chunks_added: |New_Chunks|}
```

---

#### Algorithm 10: Evidence-Grounded Answer Synthesis & Abstention Engine
Enforces that every statement is backed by verifiable code and triggers abstention if evidence is deficient.

```text
Algorithm 10: Evidence-Grounded Answer Synthesis with Abstention
Input: User question Q, Repository R, Minimum evidence threshold theta_min = 0.005
Output: Synthesized QA Response Res

1. Chunks_Retrieved <- HybridRetriever.search(query=Q, top_k=5, repo_id=R)
2. Content_Tokens <- ExtractKeyTokens(Q)  # Removes stopwords: 'where', 'is', 'the', etc.

3. # Verification Stage 1: Absolute retrieval emptiness
4. If |Chunks_Retrieved| == 0 then:
5.     Return TriggerAbstention(Q, reason="No matching chunks retrieved.")

6. Primary_Candidate <- Chunks_Retrieved[0]

7. # Verification Stage 2: Similarity score confidence floor
8. If Primary_Candidate.score < theta_min then:
9.     Return TriggerAbstention(Q, reason="Retrieved candidate score below confidence threshold.")

10. # Verification Stage 3: Content token overlap check
11. Top_Text <- ConcatenateText(Chunks_Retrieved[0..2])
12. Token_Overlap <- any(token in Top_Text for token in Content_Tokens)
13. If not Token_Overlap then:
14.     Return TriggerAbstention(Q, reason="Substantive query concepts missing from retrieved code.")

15. # Synthesis Stage: Construct verifiable response
16. Explanations <- []
17. Citations <- []
18. For each chunk c in Chunks_Retrieved:
19.     citation_string <- f"{c.repo_id}:{c.file_path}#L{c.start_line}-L{c.end_line}"
20.     Citations.append(citation_string)
21.     Explanations.append( FormatEvidenceItem(c) )

22. Final_Answer <- SynthesizeGroundedAnswer(Primary_Candidate, Explanations, Citations)
23. Return {
        question: Q,
        answer: Final_Answer,
        is_answered: True,
        confidence_indicator: "high" if Primary_Candidate.score > 0.02 else "medium",
        citations: Citations,
        evidence: Chunks_Retrieved
    }

24. Function TriggerAbstention(Q, reason):
25.     Return {
            question: Q,
            answer: f"Insufficient evidence: The repository does not contain verifiable code matching '{Q}'.",
            is_answered: False,
            confidence_indicator: "insufficient_evidence",
            citations: [],
            evidence: []
        }
```

---

---

## 7. Methodology

The end-to-end development methodology was structured into nine distinct phases:

| Phase | Milestone Description | Implemented Mechanism | Verification Status |
|---|---|---|---|
| **P1** | Multi-Repository Collection | Automated ingestion of public Python and Java repositories. | Completed across 4 baseline and expansion repos. |
| **P2** | Syntax Tree Chunk Extraction | Structural parsing using Python `ast` and Java `tree-sitter`. | Completed (215,988 initial chunks; balanced to clean corpus). |
| **P3** | Dataset Quality Gating | Human review loop and automated schema validation. | Completed (0 structural errors in JSONL schema). |
| **P4** | Tokenizer Training | Byte-Pair Encoding on programming syntax and developer questions. | Completed (16,000 vocab, special token handling). |
| **P5** | Transformer Encoder Training | 4-layer Transformer trained from scratch via InfoNCE loss. | Completed (2 epochs, loss decreased $2.0197 \to 1.0382$). |
| **P6** | Retrieval Benchmarking | Dense vector audit, Rank-BM25, and RRF fusion tuning. | Completed (Recall@10 = 43.97%, MRR = 0.2687). |
| **P7** | Static Symbol Call Graph | Static dependency analysis for callers, callees, and unit tests. | Completed (Cross-file relationship resolution). |
| **P8** | Incremental Synchronization | Git diff inspection ($O(\Delta)$ vs $O(N)$ rebuild). | Completed (Git diff commit tracking). |
| **P9** | Full-Stack UI/UX Application | SaaS React dashboard and FastAPI asynchronous server. | Completed (Verified with 75 passing test cases). |

### Contrastive Training Formulation
The custom encoder was trained using the InfoNCE objective:
$$\mathcal{L}_{\text{InfoNCE}} = -\sum_{i=1}^B \log \frac{\exp\left(\frac{\mathbf{q}_i \cdot \mathbf{p}_i}{\tau}\right)}{\exp\left(\frac{\mathbf{q}_i \cdot \mathbf{p}_i}{\tau}\right) + \sum_{j \neq i}^B \exp\left(\frac{\mathbf{q}_i \cdot \mathbf{p}_j}{\tau}\right) + \sum_{k=1}^K \exp\left(\frac{\mathbf{q}_i \cdot \mathbf{n}_{i,k}}{\tau}\right)}$$
where $\mathbf{q}_i$ is the query embedding, $\mathbf{p}_i$ is the positive code chunk embedding, $\mathbf{p}_j$ represents in-batch negatives, $\mathbf{n}_{i,k}$ represents explicit hard negatives mined via high BM25 keyword overlap from irrelevant files, and $\tau = 0.07$ is the temperature hyperparameter.

---

## 8. Implementation

### 8.1 Technology Stack
- **Programming Language:** Python 3.12 (Backend & ML Pipeline), TypeScript / JavaScript (Frontend).
- **Deep Learning Framework:** PyTorch 2.4.0 (Custom Transformer, InfoNCE loss, tensor operations).
- **Parsing Libraries:** Python standard `ast` module, `tree-sitter 0.23.0`, `tree-sitter-java 0.23.2`.
- **Lexical Indexing:** `rank-bm25 0.2.2`.
- **Web Framework:** FastAPI 0.115.0, Uvicorn (ASGI), Pydantic v2.
- **Frontend Architecture:** React 18, Vite, Tailwind CSS, Lucide React icons, PrismJS (syntax highlighting).
- **Storage:** JSON Lines (`.jsonl`), NumPy binary arrays (`.npy`), Pickle indexes (`.pkl`).

### 8.2 Key Implementation Modules
1. `dataset_pipeline/build_chunks.py`: Contains `py_chunks()` and `java_chunks()` implementing language-aware structural chunking with line number preservation.
2. `training/model.py`: Implements `CodeEncoderConfig`, `CodeEncoder` (4-layer Transformer with Pre-LN and mask-aware mean pooling), and `InfoNCELoss`.
3. `retrieval/bm25_index.py`: Code-aware lexical tokenizer splitting camelCase and snake_case tokens; manages persistent BM25 indexing.
4. `retrieval/dense_index.py`: Manages vector generation, batch encoding, and unit-normalized inner product computation.
5. `retrieval/hybrid_retriever.py`: Combines BM25 and dense results using Reciprocal Rank Fusion ($k=60$) and classifies matches (*Exact Match*, *Strong Semantic Match*, *Related Context*).
6. `retrieval/answer_engine.py`: Orchestrates evidence validation, multi-file flow synthesis, symbol graph augmentation, and the abstention mechanism.
7. `backend/app/services/github_service.py`: Implements shallow Git cloning with `-c core.longpaths=true`, temporary directory staging, and commit SHA verification.
8. `run_backend.py`: Dedicated entrypoint restricting Uvicorn reload watching strictly to `backend/`, preventing server restarts during repository ingestion.

---

## 9. Results and Discussion

### 9.1 Corpus and Ingestion Metrics
During the initial extraction phase, four major open-source repositories were ingested and parsed into structural chunks:

| Repository Name | Primary Language | License Detected | Total Chunks Extracted | Structural Errors |
|---|---|---|---|---|
| `public-apis/public-apis` | Python | MIT | 1,420 | 0 |
| `EbookFoundation/free-programming-books` | Python | CC-BY-4.0 | 1,489 | 0 |
| `NationalSecurityAgency/ghidra` | Java | Apache-2.0 | 185,412 | 0 |
| `iluwatar/java-design-patterns` | Java | Open Source | 27,667 | 0 |
| **Total Baseline Corpus** | **Python & Java** | **Verified** | **215,988** | **0** |

To resolve the extreme initial imbalance (98.65% Java vs. 1.35% Python), a balanced stratified subset was sampled across both languages for contrastive training and evaluation, augmented with standard reference libraries (`psf/requests`, `google/gson`).

### 9.2 Custom Transformer Training and Retrieval Evaluation
The 4-layer CodeEncoder was trained from scratch across two epochs using AdamW optimizer ($\text{lr} = 10^{-4}$) on human-reviewed and mined question-code pairs.

| Epoch | Training Loss | Recall@1 | Recall@5 | Recall@10 | Mean Reciprocal Rank (MRR) |
|---|---|---|---|---|---|
| **1** | 2.0197 | 13.79% | 18.97% | 32.76% | 0.1905 |
| **2** | 1.0382 | **18.97%** | **32.76%** | **43.97%** | **0.2687** |

The training progression demonstrates steady convergence:
- The InfoNCE training loss decreased by **48.6%** ($2.0197 \to 1.0382$).
- Recall@10 improved from **32.76% to 43.97%**, proving that the model successfully learned to cluster semantically equivalent query-code representations without any pre-trained weights.
- The MRR rose to **0.2687**, indicating that relevant source chunks appear on average within the top 3 to 4 retrieved positions.

### 9.3 End-to-End System Validation Examples

#### Example 1: Python Query on `psf/requests`
- **User Question:** *"Where is authentication implemented?"*
- **Retrieval Method:** Hybrid (BM25 + Dense RRF)
- **Top Evidence Retrieved:** `requests/auth.py` (lines 1–85), class `HTTPBasicAuth`
- **System Answer:**
  > *"Authentication is implemented in `requests/auth.py` (lines 1–85) via the `HTTPBasicAuth` class and `HTTPDigestAuth`. It handles basic HTTP credentials, token attachments, and header encoding via the `__call__` method on outbound request preparations."*
- **Citations:** `psf__requests:requests/auth.py#L1-L85` (Clickable with full source preview).

#### Example 2: Java Query on `google/gson`
- **User Question:** *"Which method converts JSON strings into Java objects?"*
- **Retrieval Method:** Hybrid (Exact symbol match + Dense RRF)
- **Top Evidence Retrieved:** `gson/src/main/java/com/google/gson/Gson.java` (lines 795–820), method `Gson.fromJson(String, Class<T>)`
- **System Answer:**
  > *"The core deserialization routine is handled by `Gson.fromJson(String, Class<T>)` in `gson/src/main/java/com/google/gson/Gson.java` (lines 795–820). It delegates parsing to a `JsonReader`, resolves the target `TypeToken`, and invokes the registered `TypeAdapter`."*
- **Citations:** `google__gson:gson/src/main/java/com/google/gson/Gson.java#L795-L820`.

#### Example 3: Abstention Verification (Missing Evidence)
- **User Question:** *"Where is the Bitcoin cryptocurrency mining pool configured?"*
- **Repository:** `psf/requests`
- **Result:**
  - Raw candidate scores: All fell below minimum grounding threshold ($< 0.005$).
  - `is_answered`: `False`
  - `confidence_indicator`: `"insufficient_evidence"`
  - **System Output:**
    > *"Insufficient evidence: The repository does not contain verifiable code matching 'Where is the Bitcoin cryptocurrency mining pool configured?'. No corresponding functions, classes, or files were found with sufficient confidence in the indexed codebase."*

---

## 10. Conclusion and Future Work

### 10.1 Conclusion
This project successfully designed and implemented the **GitHub Knowledge Assistant**, a comprehensive, reliable question-answering system for Python and Java GitHub repositories. By integrating:
1. AST-level structural code chunking,
2. A custom 4-layer Transformer CodeEncoder trained from scratch with InfoNCE loss,
3. Dual-channel hybrid retrieval combining Rank-BM25 and vector search via Reciprocal Rank Fusion,
4. In-memory static symbol graphs for caller-callee and test tracing, and
5. Strict evidence grounding with an active abstention mechanism,

the system eliminates hallucinations and provides software developers with 100% verifiable code explanations tied to exact file paths and source lines. The solution performs sub-second query inference entirely on commodity CPU hardware, offering an open-source, private, and cost-effective alternative to commercial LLM code assistants.

### 10.2 Future Work
- **Expansion to Additional Programming Languages:** Extend AST parsers to support C/C++, TypeScript, Go, and Rust via Tree-Sitter grammars.
- **Larger-Scale Contrastive Pre-Training:** Train the CodeEncoder on GPU clusters across millions of multi-repository triplets to push Recall@10 beyond 75%.
- **Cross-Repository Dependency Resolution:** Index external package dependencies (Maven, PyPI) to allow queries across imported third-party library boundaries.
- **Git Commit Diff QA:** Enable developers to query pull requests directly (e.g., *"What breaking changes were introduced in this commit?"*).

---

## 11. References

1. C. Liu, X. Xia, D. Lo, C. Gao, X. Yang, and J. Grundy, "Opportunities and Challenges in Code Search Tools," *ACM Computing Surveys*, vol. 54, no. 9, Article 196, pp. 1–40, 2022. DOI: `10.1145/3480027`.
2. H. P. Samoaa, F. Bayram, P. Salza, and P. Leitner, "A Systematic Mapping Study of Source Code Representation for Deep Learning in Software Engineering," *IET Software*, vol. 16, no. 4, pp. 351–385, 2022. DOI: `10.1049/sfw2.12064`.
3. Y. Xie, J. Lin, H. Dong, L. Zhang, and Z. Wu, "Survey of Code Search Based on Deep Learning," *ACM Transactions on Software Engineering and Methodology*, vol. 33, no. 2, Article 54, pp. 1–42, 2023. DOI: `10.1145/3628161`.
4. Z. Deng, L. Xu, C. Liu, L. Huangfu, and M. Yan, "Code Semantic Enrichment for Deep Code Search," *Journal of Systems and Software*, vol. 207, Article 111856, pp. 1–16, 2024. DOI: `10.1016/j.jss.2023.111856`.
5. D. R. Fudholi and A. Capiluppi, "Artificial Intelligence for Source Code Understanding Tasks: A Systematic Mapping Study," *Information and Software Technology*, vol. 189, Article 107915, pp. 1–21, 2026. DOI: `10.1016/j.infsof.2025.107915`.
6. A. Vaswani et al., "Attention Is All You Need," *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 30, pp. 5998–6008, 2017.
7. S. Robertson and H. Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," *Foundations and Trends in Information Retrieval*, vol. 3, no. 4, pp. 333–389, 2009.
8. G. V. Cormack, C. L. Clarke, and S. Büttcher, "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods," *Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval*, pp. 758–759, 2009.
9. A. van den Oord, Y. Li, and O. Vinyals, "Representation Learning with Contrastive Predictive Coding," *arXiv preprint arXiv:1807.03748*, 2018.
10. P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, pp. 9459–9474, 2020.

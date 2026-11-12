import ast
from pathlib import Path
from .common import DATA,EXT,skip,secret,sid,read,write
def py_chunks(text):
 lines=text.splitlines();tree=ast.parse(text);nodes=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
 nodes.sort(key=lambda n:n.lineno);out=[]
 for n in nodes:
  start,end=n.lineno,getattr(n,"end_lineno",n.lineno);code="\n".join(lines[start-1:end])
  if len(code)>12000:continue
  imports=sorted({a.name for x in ast.walk(n) if isinstance(x,ast.Import) for a in x.names}|{x.module or "" for x in ast.walk(n) if isinstance(x,ast.ImportFrom)})
  used=sorted({x.id for x in ast.walk(n) if isinstance(x,ast.Name)})
  out.append((type(n).__name__,n.name,code,start,end,imports,[n.name],used,"python_ast"))
 if not out and text.strip():out=[("module","module",text[:12000],1,min(len(lines),500),[],[],[],"python_ast_module")]
 return out
def java_chunks(text):
 try:
  from tree_sitter import Language,Parser
  import tree_sitter_java
  parser=Parser(Language(tree_sitter_java.language()));raw=text.encode();root=parser.parse(raw).root_node
  wanted={"class_declaration","interface_declaration","enum_declaration","method_declaration","constructor_declaration"}
  out=[];stack=[root]
  while stack:
   n=stack.pop()
   if n.type in wanted:
    code=raw[n.start_byte:n.end_byte].decode(errors="replace")
    if len(code)<=12000:
     name=next((raw[c.start_byte:c.end_byte].decode(errors="replace") for c in n.children if c.type=="identifier"),"anonymous")
     out.append((n.type,name,code,n.start_point.row+1,n.end_point.row+1,[],[name],[],"tree_sitter_java"))
   stack.extend(reversed(n.children))
  if out:return out
 except Exception:pass
 lines=text.splitlines();return [("fallback_block",f"lines_{i+1}_{min(i+80,len(lines))}","\n".join(lines[i:i+80])[:12000],i+1,min(i+80,len(lines)),[],[],[],"line_fallback") for i in range(0,len(lines),70) if "\n".join(lines[i:i+80]).strip()]
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

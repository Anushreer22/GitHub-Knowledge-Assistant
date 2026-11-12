import React, { useEffect, useState } from 'react';
import Prism from 'prismjs';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-json';
import { Copy, Check, Code, FileText } from 'lucide-react';

interface Props {
  code: string;
  language?: string | null;
  filePath?: string;
  startLine?: number;
  endLine?: number;
  highlightLines?: [number, number];
  title?: string;
}

export const CodeViewer: React.FC<Props> = ({
  code,
  language = 'python',
  filePath,
  startLine = 1,
  endLine,
  title
}) => {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    Prism.highlightAll();
  }, [code, language]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error("Failed to copy", e);
    }
  };

  const normLang = (language || 'python').toLowerCase();
  const prismLang = normLang.includes('java') && !normLang.includes('script')
    ? 'java'
    : normLang.includes('py')
    ? 'python'
    : normLang.includes('ts')
    ? 'typescript'
    : normLang.includes('json')
    ? 'json'
    : 'javascript';

  const lines = code.split('\n');

  return (
    <div className="rounded-xl overflow-hidden border border-slate-800 bg-slate-900/90 shadow-xl">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950/80 border-b border-slate-800/80">
        <div className="flex items-center gap-2 overflow-hidden text-xs">
          <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
          {filePath && (
            <span className="font-mono text-slate-300 truncate" title={filePath}>
              {filePath}
            </span>
          )}
          {startLine && endLine && (
            <span className="text-slate-500 font-mono">
              (L{startLine}–L{endLine})
            </span>
          )}
          {title && (
            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono text-[11px]">
              {title}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded">
            {prismLang}
          </span>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded transition-colors"
            title="Copy code"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Code with Line Numbers */}
      <div className="overflow-x-auto text-xs font-mono p-4 flex leading-relaxed bg-[#090d16]">
        {/* Line numbers */}
        <div className="select-none text-slate-600 text-right pr-4 border-r border-slate-800/60 font-mono shrink-0">
          {lines.map((_, i) => (
            <div key={i}>{startLine + i}</div>
          ))}
        </div>
        {/* Code Content */}
        <pre className={`pl-4 overflow-visible language-${prismLang} flex-1`}>
          <code className={`language-${prismLang}`}>{code}</code>
        </pre>
      </div>
    </div>
  );
};

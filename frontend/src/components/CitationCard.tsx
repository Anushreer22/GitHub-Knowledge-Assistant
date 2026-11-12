import React from 'react';
import { EvidenceItem } from '../types/api';
import { ClassificationBadge } from './ClassificationBadge';
import { ExternalLink, FileCode, Hash } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  evidence: EvidenceItem;
  rank?: number;
  onSelect?: () => void;
  compact?: boolean;
}

export const CitationCard: React.FC<Props> = ({ evidence, rank, onSelect, compact = false }) => {
  const repoName = evidence.repo_id.split('__').pop() || evidence.repo_id;
  const citationText = evidence.citation || `${evidence.repo_id}:${evidence.file_path}#L${evidence.start_line}-L${evidence.end_line}`;

  return (
    <div
      onClick={onSelect}
      className={`rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-850 hover:border-slate-700 transition-all p-3.5 ${
        onSelect ? 'cursor-pointer hover:shadow-lg hover:shadow-indigo-500/5' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap text-xs">
          {rank !== undefined && (
            <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center font-mono font-semibold text-[11px]">
              {rank}
            </span>
          )}
          <span className="font-semibold text-slate-200 font-mono">
            {evidence.chunk_name}
          </span>
          <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-mono bg-slate-800 text-slate-400">
            {evidence.chunk_type}
          </span>
          <ClassificationBadge classification={evidence.match_classification} />
        </div>

        <div className="text-right shrink-0">
          <span className="text-[11px] font-mono text-slate-500">
            Score: <span className="text-slate-300 font-medium">{evidence.score.toFixed(4)}</span>
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400 mb-2 font-mono truncate">
        <FileCode className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
        <span className="text-slate-500">{repoName} /</span>
        <span className="text-slate-300 truncate">{evidence.file_path}</span>
        <span className="text-slate-500 shrink-0">
          :L{evidence.start_line}-L{evidence.end_line}
        </span>
      </div>

      {!compact && evidence.code_snippet && (
        <div className="mt-2 text-xs font-mono bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/60 text-slate-300 overflow-x-auto max-h-32 leading-relaxed">
          <pre>{evidence.code_snippet}</pre>
        </div>
      )}

      {evidence.chunk_id && (
        <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
          <span className="text-slate-500 font-mono truncate">
            ID: {evidence.chunk_id}
          </span>
          <Link
            to={`/evidence/${encodeURIComponent(evidence.repo_id)}/${encodeURIComponent(evidence.chunk_id)}`}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            Inspect Chunk <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      )}
    </div>
  );
};

import React from 'react';
import { MatchClassification } from '../types/api';
import { CheckCircle2, Sparkles, Layers, AlertCircle } from 'lucide-react';

interface Props {
  classification?: MatchClassification;
  className?: string;
}

export const ClassificationBadge: React.FC<Props> = ({ classification, className = '' }) => {
  switch (classification) {
    case 'exact_match':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 ${className}`}>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          Exact Match
        </span>
      );
    case 'strong_semantic_match':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 ${className}`}>
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          Strong Semantic
        </span>
      );
    case 'related_context':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 ${className}`}>
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          Related Context
        </span>
      );
    case 'insufficient_evidence':
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700 ${className}`}>
          <AlertCircle className="w-3.5 h-3.5 text-slate-400" />
          Insufficient Evidence
        </span>
      );
  }
};

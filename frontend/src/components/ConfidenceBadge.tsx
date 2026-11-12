import React from 'react';
import { ConfidenceIndicator } from '../types/api';
import { ShieldCheck, AlertTriangle, AlertOctagon, HelpCircle } from 'lucide-react';

interface Props {
  confidence: ConfidenceIndicator;
  className?: string;
}

export const ConfidenceBadge: React.FC<Props> = ({ confidence, className = '' }) => {
  switch (confidence) {
    case 'high':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 ${className}`}>
          <ShieldCheck className="w-3.5 h-3.5" />
          High Confidence
        </span>
      );
    case 'medium':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-950/80 text-amber-400 border border-amber-800/60 ${className}`}>
          <AlertTriangle className="w-3.5 h-3.5" />
          Medium Confidence
        </span>
      );
    case 'low':
      return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-950/80 text-rose-400 border border-rose-800/60 ${className}`}>
          <AlertOctagon className="w-3.5 h-3.5" />
          Low Confidence
        </span>
      );
    case 'insufficient_evidence':
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700 ${className}`}>
          <HelpCircle className="w-3.5 h-3.5" />
          Insufficient Evidence
        </span>
      );
  }
};

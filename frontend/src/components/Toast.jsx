import React, { useEffect } from 'react';
import { Radio, X, AlertTriangle, Flame } from 'lucide-react';

export function Toast({ toast, onDismiss }) {
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => {
      onDismiss();
    }, 7000);
    return () => clearTimeout(timer);
  }, [toast, onDismiss]);

  if (!toast) return null;

  const isAnomaly = toast.type === 'anomaly';
  const isAlert = toast.severity === 'ALERT';

  return (
    <div className={`fixed bottom-5 right-5 z-50 flex items-center gap-3 text-white px-4 py-3 rounded-xl shadow-2xl border backdrop-blur-md animate-bounce-short max-w-sm transition-all ${
      isAnomaly
        ? isAlert
          ? 'bg-red-950/95 border-[#C1444B] ring-2 ring-[#C1444B]/50'
          : 'bg-amber-950/95 border-[#E8A33D] ring-2 ring-[#E8A33D]/50'
        : 'bg-slate-900/95 border-slate-700/80'
    }`}>
      <div className={`p-2 rounded-lg border ${
        isAnomaly
          ? isAlert
            ? 'bg-[#C1444B]/30 text-[#C1444B] border-[#C1444B]/50'
            : 'bg-[#E8A33D]/30 text-[#E8A33D] border-[#E8A33D]/50'
          : 'bg-[#1F5B8C]/40 text-blue-300 border-blue-400/30'
      }`}>
        {isAnomaly ? (
          isAlert ? <Flame className="w-5 h-5 animate-bounce" /> : <AlertTriangle className="w-5 h-5 animate-pulse" />
        ) : (
          <Radio className="w-4 h-4 animate-pulse" />
        )}
      </div>

      <div className="flex-1">
        <div className="flex items-center gap-1.5">
          <span className={`text-xs font-extrabold uppercase tracking-wide ${
            isAnomaly
              ? isAlert ? 'text-[#C1444B]' : 'text-[#E8A33D]'
              : 'text-white'
          }`}>
            {isAnomaly ? '🔺 ANOMALY SIGNAL DETECTED' : 'Live Alert Broadcast'}
          </span>
          <span className="text-[10px] text-slate-400">({toast.time})</span>
        </div>
        <p className="text-xs font-semibold text-slate-100 mt-0.5">
          {isAnomaly ? (
            toast.message
          ) : (
            <>New report: <span className="font-bold text-amber-300">{toast.eventType}</span> in {toast.city || toast.state}</>
          )}
        </p>
      </div>

      <button
        onClick={onDismiss}
        className="text-slate-400 hover:text-white p-1 rounded-md transition"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

import React from 'react';
import { AlertTriangle, Flame } from 'lucide-react';

export function AnomalyBanner({ anomalies }) {
  if (!anomalies || anomalies.length === 0) return null;

  return (
    <div className="mb-6 bg-white border border-slate-200/90 rounded-xl p-4 shadow-card animate-fade-in">
      <div className="flex items-center gap-2 mb-3">
        <span className="flex h-2.5 w-2.5 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#C1444B] opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#C1444B]"></span>
        </span>
        <h3 className="text-xs font-bold text-[#202325] tracking-wide uppercase flex items-center gap-1.5">
          <span>🔺</span> {anomalies.length} unusual activity cluster{anomalies.length > 1 ? 's' : ''} detected
        </h3>
      </div>

      <div className="flex flex-wrap gap-2.5">
        {anomalies.map((sig, idx) => {
          const isAlert = sig.severity === 'ALERT';
          const rawType = sig.eventType || 'Weather';
          const formattedType = rawType.charAt(0).toUpperCase() + rawType.slice(1).toLowerCase().replace('_', ' ');

          return (
            <div
              key={`${sig.city}-${sig.eventType}-${idx}`}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold border ${
                isAlert
                  ? 'bg-[#C1444B]/10 text-[#C1444B] border-[#C1444B]/30'
                  : 'bg-[#E8A33D]/10 text-[#B47012] border-[#E8A33D]/40'
              }`}
            >
              {isAlert ? (
                <Flame className="w-4 h-4 shrink-0 text-[#C1444B] animate-pulse" />
              ) : (
                <AlertTriangle className="w-4 h-4 shrink-0 text-[#E8A33D]" />
              )}
              <span>
                <strong>{formattedType} cluster in {sig.city}{sig.state ? `, ${sig.state}` : ''}</strong> — {sig.reportCount} reports in {sig.windowHours || 3}h
              </span>
              <span
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                  isAlert ? 'bg-[#C1444B] text-white' : 'bg-[#E8A33D] text-white'
                }`}
              >
                {sig.severity}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

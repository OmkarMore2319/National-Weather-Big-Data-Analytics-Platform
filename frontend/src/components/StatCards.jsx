import React from 'react';
import { Activity, CheckCircle2, AlertTriangle, ShieldAlert, BarChart3, MapPin } from 'lucide-react';

export function StatCards({ summary, loading }) {
  if (loading && !summary) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-xl p-5 border border-slate-200 shadow-card animate-pulse">
            <div className="h-4 bg-slate-200 rounded w-1/2 mb-3"></div>
            <div className="h-8 bg-slate-200 rounded w-3/4 mb-2"></div>
            <div className="h-3 bg-slate-200 rounded w-1/3"></div>
          </div>
        ))}
      </div>
    );
  }

  const total = summary?.totalToday ?? 0;
  const pctVerified = summary?.pctVerified ?? 0;
  const topType = summary?.topEventType ?? 'N/A';
  const state = summary?.mostAffectedState ?? 'N/A';
  const byStatus = summary?.byStatus || {};

  return (
    <div className="space-y-3 mb-6">
      {/* 4 Main Stat Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Reports Today */}
        <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-card hover:shadow-elevated transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">Total Reports Today</span>
            <div className="p-2 rounded-lg bg-blue-50 text-[#1F5B8C]">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-[#202325]">{total}</div>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
            <span className="font-medium text-[#1F5B8C]">Multi-source</span> aggregated intake
          </p>
        </div>

        {/* Verification Rate */}
        <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-card hover:shadow-elevated transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">Verification Rate</span>
            <div className="p-2 rounded-lg bg-emerald-50 text-[#2E8B57]">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-[#2E8B57]">{pctVerified}%</div>
          <p className="text-xs text-slate-500 mt-1">
            <span className="font-semibold text-[#2E8B57]">{byStatus.VERIFIED || 0}</span> confirmed by ML & official readings
          </p>
        </div>

        {/* Top Event Type */}
        <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-card hover:shadow-elevated transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">Predominant Hazard</span>
            <div className="p-2 rounded-lg bg-amber-50 text-[#E8A33D]">
              <BarChart3 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-[#202325] truncate">{topType}</div>
          <p className="text-xs text-slate-500 mt-1">
            Highest frequency cluster across India
          </p>
        </div>

        {/* High Alert State */}
        <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-card hover:shadow-elevated transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">High Alert Region</span>
            <div className="p-2 rounded-lg bg-blue-50 text-[#1F5B8C]">
              <MapPin className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-[#202325] truncate">{state}</div>
          <p className="text-xs text-slate-500 mt-1">
            Most active reporting density
          </p>
        </div>
      </div>

      {/* Verification Status Breakdown Badges bar */}
      <div className="bg-white rounded-lg px-4 py-2.5 border border-slate-200 shadow-subtle flex flex-wrap items-center justify-between gap-3 text-xs">
        <span className="font-semibold text-slate-600">Status Distribution:</span>
        <div className="flex flex-wrap items-center gap-2">
          {/* VERIFIED (Green) */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#2E8B57]/10 text-[#2E8B57] font-semibold border border-[#2E8B57]/20">
            <span className="w-2 h-2 rounded-full bg-[#2E8B57]"></span>
            VERIFIED: {byStatus.VERIFIED || 0}
          </span>

          {/* PENDING (Amber) */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#E8A33D]/10 text-[#E8A33D] font-semibold border border-[#E8A33D]/20">
            <span className="w-2 h-2 rounded-full bg-[#E8A33D]"></span>
            PENDING: {byStatus.PENDING || 0}
          </span>

          {/* SUSPICIOUS (Critical Red - ONLY red on whole dashboard!) */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#C1444B]/10 text-[#C1444B] font-semibold border border-[#C1444B]/20">
            <span className="w-2 h-2 rounded-full bg-[#C1444B]"></span>
            SUSPICIOUS: {byStatus.SUSPICIOUS || 0}
          </span>

          {/* DUPLICATE (Muted Grey) */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 font-semibold border border-slate-200">
            <span className="w-2 h-2 rounded-full bg-slate-400"></span>
            DUPLICATE: {byStatus.DUPLICATE || 0}
          </span>
        </div>
      </div>
    </div>
  );
}

import React from 'react';
import { Filter, Search, Calendar, RotateCcw, Check } from 'lucide-react';

const EVENT_TYPES = [
  { id: 'RAINFALL', label: 'Rainfall', color: '#1F5B8C' },
  { id: 'THUNDERSTORM', label: 'Thunderstorm', color: '#7C3AED' },
  { id: 'FLOODING', label: 'Flooding', color: '#0D9488' },
  { id: 'HEATWAVE', label: 'Heatwave', color: '#D97706' },
  { id: 'FOG', label: 'Fog / Smog', color: '#64748B' },
  { id: 'DUST_STORM', label: 'Dust Storm', color: '#B45309' },
  { id: 'STRONG_WIND', label: 'Strong Wind', color: '#0284C7' },
];

const STATUS_OPTIONS = [
  { id: '', label: 'All Statuses' },
  { id: 'VERIFIED', label: 'Verified Only' },
  { id: 'PENDING', label: 'Pending Review' },
  { id: 'SUSPICIOUS', label: 'Suspicious / Flagged' },
  { id: 'DUPLICATE', label: 'Duplicates' },
];

export function FilterBar({ filters, setFilters, onReset }) {
  // Toggle eventType in multi-select array
  const toggleEventType = (typeId) => {
    const currentTypes = filters.eventType ? filters.eventType.split(',').filter(Boolean) : [];
    let updated;
    if (currentTypes.includes(typeId)) {
      updated = currentTypes.filter(t => t !== typeId);
    } else {
      updated = [...currentTypes, typeId];
    }
    setFilters(prev => ({
      ...prev,
      eventType: updated.join(',')
    }));
  };

  const selectedEventTypes = filters.eventType ? filters.eventType.split(',').filter(Boolean) : [];

  return (
    <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-subtle mb-6 space-y-3">
      {/* Top row: Search input, Status select, Date presets */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* City / State Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by city or state (e.g. Mumbai, Delhi, Rajasthan)..."
            value={filters.city || ''}
            onChange={(e) => setFilters(prev => ({ ...prev, city: e.target.value }))}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1F5B8C]/20 focus:border-[#1F5B8C] transition"
          />
        </div>

        {/* Verification Status Selector */}
        <div className="w-full md:w-52">
          <select
            value={filters.status || ''}
            onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
            className="w-full py-2 px-3 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1F5B8C]/20 focus:border-[#1F5B8C] bg-white transition"
          >
            {STATUS_OPTIONS.map(opt => (
              <option key={opt.id} value={opt.id}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Date presets */}
        <div className="flex items-center space-x-1">
          <button
            onClick={() => {
              const d = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
              setFilters(prev => ({ ...prev, from: d, to: '' }));
            }}
            className={`px-2.5 py-1.5 rounded-md text-xs font-medium border transition ${
              filters.from && !filters.to ? 'bg-[#1F5B8C] text-white border-[#1F5B8C]' : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            24h
          </button>
          <button
            onClick={() => {
              const d = new Date(Date.now() - 3 * 24 * 3600 * 1000).toISOString();
              setFilters(prev => ({ ...prev, from: d, to: '' }));
            }}
            className="px-2.5 py-1.5 rounded-md text-xs font-medium border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 transition"
          >
            3 Days
          </button>
          <button
            onClick={onReset}
            title="Reset Filters"
            className="p-1.5 rounded-md text-xs font-medium border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 transition"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Multi-Select Event Type Pills */}
      <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-slate-100">
        <span className="text-[11px] font-semibold text-slate-500 mr-1 uppercase tracking-wider">Hazard Filter:</span>
        {EVENT_TYPES.map(type => {
          const isSelected = selectedEventTypes.includes(type.id);
          return (
            <button
              key={type.id}
              onClick={() => toggleEventType(type.id)}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                isSelected
                  ? 'text-white shadow-sm ring-1 ring-black/10'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
              style={{
                backgroundColor: isSelected ? type.color : undefined
              }}
            >
              {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
              <span>{type.label}</span>
            </button>
          );
        })}

        {selectedEventTypes.length > 0 && (
          <button
            onClick={() => setFilters(prev => ({ ...prev, eventType: '' }))}
            className="text-[11px] text-[#1F5B8C] hover:underline font-semibold ml-2"
          >
            Select All
          </button>
        )}
      </div>
    </div>
  );
}

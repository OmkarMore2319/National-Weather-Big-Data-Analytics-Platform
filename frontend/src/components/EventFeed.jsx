import React, { useState } from 'react';
import { Search, Image, ExternalLink, ShieldCheck, AlertCircle, AlertTriangle, Copy } from 'lucide-react';

const EVENT_TYPE_COLORS = {
  RAINFALL: 'bg-[#1F5B8C] text-white',
  THUNDERSTORM: 'bg-[#7C3AED] text-white',
  FLOODING: 'bg-[#0D9488] text-white',
  HEATWAVE: 'bg-[#D97706] text-white',
  FOG: 'bg-[#64748B] text-white',
  DUST_STORM: 'bg-[#B45309] text-white',
  STRONG_WIND: 'bg-[#0284C7] text-white',
  UNKNOWN: 'bg-slate-400 text-white'
};

export function EventFeed({ events, selectedEvent, onSelectEvent }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = events.filter(e => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (e.city && e.city.toLowerCase().includes(term)) ||
      (e.state && e.state.toLowerCase().includes(term)) ||
      (e.rawText && e.rawText.toLowerCase().includes(term)) ||
      (e.eventType && e.eventType.toLowerCase().includes(term))
    );
  });

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-card flex flex-col h-[520px]">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-[#202325]">Live Intelligence Feed</h3>
          <p className="text-xs text-slate-500">{filtered.length} reports in active window</p>
        </div>
        <div className="relative w-44">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search feed..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-2 py-1 text-xs rounded-md border border-slate-200 focus:outline-none focus:ring-1 focus:ring-[#1F5B8C]"
          />
        </div>
      </div>

      {/* Feed List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100 p-2 space-y-1.5">
        {filtered.length === 0 ? (
          <div className="text-center py-16 text-slate-400 text-xs">
            No weather events match current criteria.
          </div>
        ) : (
          filtered.map(event => {
            const isSelected = selectedEvent?.id === event.id;
            const isReddit = event.source === 'SOCIAL_REAL' || event.sourceMeta?.platform === 'reddit' || event.sourceMeta?.subSource === 'reddit';
            const isSimulated = !isReddit && (event.source === 'SOCIAL_SIMULATED' || event.sourceMeta?.simulated);

            return (
              <div
                key={event.id}
                onClick={() => onSelectEvent(event)}
                className={`p-3 rounded-lg cursor-pointer transition-all border ${
                  isSelected
                    ? 'bg-blue-50/70 border-[#1F5B8C] shadow-sm'
                    : 'bg-white hover:bg-slate-50/80 border-slate-100'
                }`}
              >
                {/* Header row: Hazard tag + Social badges + Time */}
                <div className="flex items-center justify-between gap-1.5 mb-1.5">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${EVENT_TYPE_COLORS[event.eventType] || 'bg-slate-500 text-white'}`}>
                      {event.eventType}
                    </span>

                    {/* Distinct Social Source Badges */}
                    {isReddit && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">
                        (Reddit)
                      </span>
                    )}

                    {isSimulated && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700 border border-purple-200">
                        (Simulated Feed)
                      </span>
                    )}

                    {event.mediaUrls && event.mediaUrls.length > 0 && (
                      <span className="text-slate-400" title="Media evidence attached">
                        <Image className="w-3.5 h-3.5" />
                      </span>
                    )}
                  </div>

                  <span className="text-[10px] text-slate-400">
                    {new Date(event.reportedAt || event.ingestedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                {/* Raw Text Snippet */}
                <p className="text-xs text-slate-700 line-clamp-2 mb-2 font-normal">
                  {event.rawText}
                </p>

                {/* Bottom Row: Location + Verification Status & Trust Score */}
                <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100/60">
                  <span className="text-[11px] font-medium text-slate-500 truncate max-w-[140px]">
                    📍 {event.city ? `${event.city}, ` : ''}{event.state}
                  </span>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold text-slate-600">
                      {event.trustScore}%
                    </span>

                    {/* Status Badge */}
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        event.verificationStatus === 'VERIFIED'
                          ? 'bg-[#2E8B57]/10 text-[#2E8B57] border border-[#2E8B57]/30'
                          : event.verificationStatus === 'PENDING'
                          ? 'bg-[#E8A33D]/10 text-[#E8A33D] border border-dashed border-[#E8A33D]/40'
                          : event.verificationStatus === 'SUSPICIOUS'
                          ? 'bg-[#C1444B]/10 text-[#C1444B] border border-[#C1444B]/30'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {event.verificationStatus}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

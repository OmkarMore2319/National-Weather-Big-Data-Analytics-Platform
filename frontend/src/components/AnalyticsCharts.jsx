import React, { useState, useEffect, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import { api } from '../services/api';
import { Filter } from 'lucide-react';

const STATUS_COLORS = {
  VERIFIED: '#2E8B57',    // Green
  PENDING: '#E8A33D',     // Amber
  SUSPICIOUS: '#C1444B',  // ONLY red on page
  REJECTED: '#64748B'     // Cool Slate
};

export function AnalyticsCharts({ summary, events, onSelectStatusFilter }) {
  const [selectedLocation, setSelectedLocation] = useState('');
  const [scopedEvents, setScopedEvents] = useState(null);
  const [isLoadingScope, setIsLoadingScope] = useState(false);

  // Extract unique states and cities from current events for location scope dropdown
  const locationOptions = useMemo(() => {
    if (!events || events.length === 0) return { states: [], cities: [] };
    const states = new Set();
    const cities = new Set();

    events.forEach(e => {
      if (e.state && e.state.trim()) states.add(e.state.trim());
      if (e.city && e.city.trim()) cities.add(e.city.trim());
    });

    return {
      states: Array.from(states).sort(),
      cities: Array.from(cities).sort()
    };
  }, [events]);

  // Re-query GET /api/v1/events filtered by city/state when scope changes
  useEffect(() => {
    if (!selectedLocation) {
      setScopedEvents(null);
      return;
    }
    const [kind, name] = selectedLocation.split(':');
    if (!name) {
      setScopedEvents(null);
      return;
    }

    setIsLoadingScope(true);
    const queryParams = kind === 'state' ? { state: name } : { city: name };

    api.getEvents(queryParams)
      .then(data => {
        setScopedEvents(data || []);
      })
      .catch(err => {
        console.error('[AnalyticsCharts] Error fetching location-scoped events:', err);
      })
      .finally(() => {
        setIsLoadingScope(false);
      });
  }, [selectedLocation]);

  if (!summary) return null;

  // Active events dataset for distribution chart
  const activeDataset = scopedEvents !== null ? scopedEvents : events;

  // Prepare STACKED Bar Data (VERIFIED, PENDING, SUSPICIOUS -- excluding REJECTED and DUPLICATE)
  const hazardTypes = ['RAINFALL', 'THUNDERSTORM', 'FLOODING', 'HEATWAVE', 'FOG', 'DUST_STORM', 'STRONG_WIND', 'UNKNOWN'];

  const stackedBarData = hazardTypes.map(hType => {
    const matching = activeDataset.filter(e => e.eventType === hType);
    const verified = matching.filter(e => e.verificationStatus === 'VERIFIED').length;
    const pending = matching.filter(e => e.verificationStatus === 'PENDING').length;
    const suspicious = matching.filter(e => e.verificationStatus === 'SUSPICIOUS').length;
    return {
      type: hType,
      VERIFIED: verified,
      PENDING: pending,
      SUSPICIOUS: suspicious,
      total: verified + pending + suspicious
    };
  }).filter(d => d.total > 0 || selectedLocation !== '');

  // Calculate Verification Pipeline Headline Stat
  const rawCount = events.length;
  const duplicateCount = events.filter(e => e.verificationStatus === 'DUPLICATE').length;
  const uniqueCount = rawCount - duplicateCount;
  const dedupPercent = rawCount > 0 ? Math.round((duplicateCount / rawCount) * 100) : 0;

  // Prepare Donut Data (EXCLUDES DUPLICATE)
  const statusCounts = {
    VERIFIED: events.filter(e => e.verificationStatus === 'VERIFIED').length,
    PENDING: events.filter(e => e.verificationStatus === 'PENDING').length,
    SUSPICIOUS: events.filter(e => e.verificationStatus === 'SUSPICIOUS').length,
    REJECTED: events.filter(e => e.verificationStatus === 'REJECTED').length
  };

  const statusData = [
    { name: 'VERIFIED', value: statusCounts.VERIFIED, color: STATUS_COLORS.VERIFIED },
    { name: 'PENDING', value: statusCounts.PENDING, color: STATUS_COLORS.PENDING },
    { name: 'SUSPICIOUS', value: statusCounts.SUSPICIOUS, color: STATUS_COLORS.SUSPICIOUS },
    { name: 'REJECTED', value: statusCounts.REJECTED, color: STATUS_COLORS.REJECTED }
  ].filter(d => d.value > 0);

  const nonDupTotal = statusData.reduce((acc, curr) => acc + curr.value, 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
      {/* Event Hazard Distribution STACKED Bar Chart */}
      <div className="lg:col-span-2 bg-white rounded-xl p-5 border border-slate-200/80 shadow-card flex flex-col justify-between">
        <div>
          {/* Header row with Location Scope Selector */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
            <div>
              <h3 className="text-sm font-bold text-[#202325]">Weather Event Distribution by Hazard Type</h3>
              <p className="text-xs text-slate-500">
                Stacked breakdown by verification status ({selectedLocation ? selectedLocation.split(':')[1] : 'All India'})
              </p>
            </div>

            {/* Location Scope Dropdown */}
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={selectedLocation}
                onChange={(e) => setSelectedLocation(e.target.value)}
                className="py-1.5 px-2.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1F5B8C]/20 focus:border-[#1F5B8C] bg-white font-medium text-slate-700 shadow-sm"
              >
                <option value="">All India (Default)</option>
                {locationOptions.states.length > 0 && (
                  <optgroup label="States">
                    {locationOptions.states.map(st => (
                      <option key={`state-${st}`} value={`state:${st}`}>{st} (State)</option>
                    ))}
                  </optgroup>
                )}
                {locationOptions.cities.length > 0 && (
                  <optgroup label="Cities">
                    {locationOptions.cities.map(ct => (
                      <option key={`city-${ct}`} value={`city:${ct}`}>{ct} (City)</option>
                    ))}
                  </optgroup>
                )}
              </select>
            </div>
          </div>

          {/* Stacked Chart Container */}
          <div className="h-64 w-full relative">
            {isLoadingScope && (
              <div className="absolute inset-0 bg-white/70 backdrop-blur-[1px] z-10 flex items-center justify-center text-xs font-semibold text-[#1F5B8C]">
                Filtering data for {selectedLocation.split(':')[1]}...
              </div>
            )}

            {stackedBarData.length === 0 ? (
              <div className="flex items-center justify-center h-full text-xs text-slate-400">
                No hazard distribution data available for selected location scope.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stackedBarData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                  <XAxis
                    dataKey="type"
                    tick={{ fontSize: 10, fill: '#64748B' }}
                    angle={-25}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#64748B' }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      fontSize: '12px',
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
                    }}
                    formatter={(value, name) => [`${value} reports`, name]}
                  />
                  <Legend
                    verticalAlign="top"
                    align="right"
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{ fontSize: '11px', paddingBottom: '8px' }}
                  />
                  <Bar dataKey="VERIFIED" stackId="hazardStack" fill="#2E8B57" name="Verified" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="PENDING" stackId="hazardStack" fill="#E8A33D" name="Pending" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="SUSPICIOUS" stackId="hazardStack" fill="#C1444B" name="Suspicious" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Verification Status Distribution Donut */}
      <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-card flex flex-col justify-between">
        <div>
          <div className="mb-2">
            <h3 className="text-sm font-bold text-[#202325]">Verification Pipeline Status</h3>
            <p className="text-xs text-slate-500">Real-time trust triage classification</p>
          </div>

          {/* Headline Stat above Donut */}
          <div className="text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200/80 rounded-lg p-2.5 mb-3 text-center shadow-subtle">
            <span className="text-[#1F5B8C] font-bold">{rawCount}</span> raw reports &rarr; <span className="text-slate-900 font-bold">{uniqueCount}</span> unique events ({dedupPercent}% deduplicated)
          </div>

          <div className="h-56 w-full flex items-center justify-center">
            {statusData.length === 0 ? (
              <div className="text-xs text-slate-400">No status metrics available</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusData}
                    cx="50%"
                    cy="45%"
                    innerRadius={48}
                    outerRadius={72}
                    paddingAngle={3}
                    dataKey="value"
                    cursor="pointer"
                    onClick={(entry) => {
                      if (onSelectStatusFilter && entry && entry.name) {
                        onSelectStatusFilter(entry.name);
                      }
                    }}
                  >
                    {statusData.map((entry, index) => (
                      <Cell key={`status-${index}`} fill={entry.color} cursor="pointer" />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      fontSize: '12px'
                    }}
                    formatter={(value, name) => [
                      `${value} events (${nonDupTotal > 0 ? Math.round((value / nonDupTotal) * 100) : 0}%) (Click to filter feed)`,
                      name
                    ]}
                  />
                  <Legend
                    verticalAlign="bottom"
                    align="center"
                    iconType="circle"
                    iconSize={8}
                    formatter={(value) => (
                      <span
                        className="text-xs text-slate-700 font-semibold cursor-pointer hover:underline"
                        onClick={() => onSelectStatusFilter && onSelectStatusFilter(value)}
                        title={`Filter feed by ${value}`}
                      >
                        {value}
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

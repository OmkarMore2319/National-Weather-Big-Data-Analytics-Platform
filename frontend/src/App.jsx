import React, { useState } from 'react';
import { useLiveEvents } from './hooks/useLiveEvents';
import { Navbar } from './components/Navbar';
import { StatCards } from './components/StatCards';
import { FilterBar } from './components/FilterBar';
import { AnomalyBanner } from './components/AnomalyBanner';
import { WeatherMap } from './components/WeatherMap';
import { EventFeed } from './components/EventFeed';
import { AnalyticsCharts } from './components/AnalyticsCharts';
import { AdminPanel } from './components/AdminPanel';
import { Toast } from './components/Toast';
import { CitizenReportModal } from './components/CitizenReportModal';
import { PlusCircle, AlertCircle, RefreshCw } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('public'); // 'public' | 'admin'
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isCitizenModalOpen, setIsCitizenModalOpen] = useState(false);

  // Filters state
  const [filters, setFilters] = useState({
    eventType: '',
    status: '',
    city: '',
    state: '',
    from: '',
    to: ''
  });

  const {
    events,
    summary,
    anomalies,
    loading,
    error,
    connectionStatus,
    newEventsToast,
    anomalyToast,
    dismissToast,
    dismissAnomalyToast,
    refreshData
  } = useLiveEvents(filters);

  const handleResetFilters = () => {
    setFilters({
      eventType: '',
      status: '',
      city: '',
      state: '',
      from: '',
      to: ''
    });
  };

  return (
    <div className="min-h-screen bg-[#F7F9FA] text-[#202325] flex flex-col font-sans">
      {/* Top Government Platform Header */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        connectionStatus={connectionStatus}
        totalEventsCount={events.length}
        onRefresh={refreshData}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'public' ? (
          <div>
            {/* Top Stat Summary Cards */}
            <StatCards summary={summary} loading={loading} />

            {/* Interactive Filter Bar */}
            <FilterBar
              filters={filters}
              setFilters={setFilters}
              onReset={handleResetFilters}
            />

            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 p-4 rounded-xl text-xs text-[#C1444B] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span><b>Connection Error:</b> {error}</span>
                </div>
                <button
                  onClick={refreshData}
                  className="px-3 py-1 bg-white border border-red-200 rounded-md text-xs font-semibold hover:bg-red-50 flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" /> Retry
                </button>
              </div>
            )}

            {/* Live Anomaly Signal Badge/Banner above Map */}
            <AnomalyBanner anomalies={anomalies} />

            {/* Map and Feed Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
              {/* Leaflet Geospatial Map (8 cols on desktop) */}
              <div className="lg:col-span-8">
                <WeatherMap
                  events={events}
                  selectedEvent={selectedEvent}
                  onSelectEvent={setSelectedEvent}
                />
              </div>

              {/* Feed List (4 cols on desktop) */}
              <div className="lg:col-span-4">
                <EventFeed
                  events={events}
                  selectedEvent={selectedEvent}
                  onSelectEvent={setSelectedEvent}
                />
              </div>
            </div>

            {/* Recharts Analytics Charts Section */}
            <AnalyticsCharts
              summary={summary}
              events={events}
              onSelectStatusFilter={(status) => {
                setFilters(prev => ({
                  ...prev,
                  status: prev.status === status ? '' : status
                }));
              }}
            />
          </div>
        ) : (
          /* Admin Gated Console */
          <AdminPanel onEventUpdated={refreshData} />
        )}
      </main>

      {/* Floating Action Button: Submit Citizen Report */}
      <button
        onClick={() => setIsCitizenModalOpen(true)}
        className="fixed bottom-6 left-6 z-40 bg-[#1F5B8C] hover:bg-[#184870] text-white px-4 py-2.5 rounded-full shadow-elevated border border-blue-400/30 flex items-center gap-2 text-xs font-semibold transition-transform hover:scale-105"
      >
        <PlusCircle className="w-4 h-4" />
        <span>Report Weather Incident</span>
      </button>

      {/* Live WebSocket Toast (Prioritizes Anomaly Toast over standard event Toast) */}
      <Toast
        toast={anomalyToast || newEventsToast}
        onDismiss={anomalyToast ? dismissAnomalyToast : dismissToast}
      />

      {/* Citizen Report Modal */}
      <CitizenReportModal
        isOpen={isCitizenModalOpen}
        onClose={() => setIsCitizenModalOpen(false)}
        onSuccess={refreshData}
      />

      {/* Standard Government Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4">
          <p className="font-semibold text-slate-700">
            National Weather Big Data Analytics Platform (Problem Statement 26069)
          </p>
          <p className="text-[11px] text-slate-400 mt-1">
            Built strictly in accordance with Shared Technical Contract v2 &bull; Multi-source AI/ML Verification Ground Truth Engine
          </p>
        </div>
      </footer>
    </div>
  );
}

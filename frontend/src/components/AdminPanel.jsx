import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle,
  XCircle,
  Copy,
  Lock,
  Unlock,
  History,
  AlertCircle,
  ArrowUpDown,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  FileText,
  Download,
  Radio,
  Code,
  Flame,
  AlertTriangle,
  Info
} from 'lucide-react';

export function AdminPanel({ onEventUpdated }) {
  const [adminToken, setAdminToken] = useState(() => localStorage.getItem('weather_admin_token') || '');
  const [inputToken, setInputToken] = useState('');
  const [adminUsername, setAdminUsername] = useState(() => localStorage.getItem('weather_admin_user') || 'admin_officer');
  
  const [allEvents, setAllEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [capAlerts, setCapAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('triage'); // 'triage' | 'cap_history' | 'audit'
  const [queueFilter, setQueueFilter] = useState('triage'); // 'triage' | 'verified' | 'all'

  // Override Action Modal State
  const [overrideModal, setOverrideModal] = useState({
    isOpen: false,
    newStatus: '',
    reason: '',
    duplicateOfId: ''
  });

  // CAP Alert Modal State
  const [capModal, setCapModal] = useState({
    isOpen: false,
    alert: null,
    loading: false,
    copied: false
  });

  const [submitting, setSubmitting] = useState(false);

  // Fetch all events, audit logs, and CAP alerts history
  const fetchAdminData = async () => {
    if (!adminToken) return;
    setLoading(true);
    setError(null);
    try {
      const [eventsData, logs, alerts] = await Promise.all([
        api.getEvents(),
        api.getAdminAuditLog(adminToken),
        api.getCapAlerts(adminToken).catch(() => [])
      ]);

      setAllEvents(eventsData || []);
      setAuditLogs(logs || []);
      setCapAlerts(alerts || []);

      // Auto-select event if needed
      const filtered = (eventsData || []).filter(e => {
        if (queueFilter === 'triage') return e.verificationStatus === 'PENDING' || e.verificationStatus === 'SUSPICIOUS';
        if (queueFilter === 'verified') return e.verificationStatus === 'VERIFIED';
        return true;
      });

      if (filtered.length > 0 && (!selectedEvent || !filtered.some(e => e.id === selectedEvent.id))) {
        setSelectedEvent(filtered[0]);
      } else if (filtered.length === 0) {
        setSelectedEvent(null);
      }
    } catch (err) {
      setError(err.message || 'Failed to load admin records. Check your token.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (adminToken) {
      fetchAdminData();
    }
  }, [adminToken, queueFilter]);

  const handleLogin = (e) => {
    e.preventDefault();
    if (!inputToken.trim()) return;
    localStorage.setItem('weather_admin_token', inputToken.trim());
    localStorage.setItem('weather_admin_user', adminUsername.trim());
    setAdminToken(inputToken.trim());
  };

  const handleLogout = () => {
    localStorage.removeItem('weather_admin_token');
    setAdminToken('');
    setInputToken('');
    setAllEvents([]);
    setSelectedEvent(null);
    setCapAlerts([]);
  };

  const openOverrideModal = (status) => {
    setOverrideModal({
      isOpen: true,
      newStatus: status,
      reason: status === 'VERIFIED'
        ? 'Verified after manual review of ground telemetry and photo timestamp'
        : status === 'REJECTED'
        ? 'Rejected due to contradictory IMD station reading or falsified report'
        : 'Identified as duplicate report from existing incident cluster',
      duplicateOfId: ''
    });
  };

  const handleExecuteOverride = async () => {
    if (!selectedEvent || !overrideModal.newStatus) return;
    setSubmitting(true);
    try {
      await api.submitAdminOverride(
        selectedEvent.id,
        {
          adminUsername,
          newStatus: overrideModal.newStatus,
          reason: overrideModal.reason
        },
        adminToken
      );

      setOverrideModal({ isOpen: false, newStatus: '', reason: '', duplicateOfId: '' });
      await fetchAdminData();
      if (onEventUpdated) onEventUpdated();
    } catch (err) {
      alert(`Override failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  // Trigger CAP v1.2 Alert Generation
  const handleGenerateCapAlert = async () => {
    if (!selectedEvent || selectedEvent.verificationStatus !== 'VERIFIED') return;
    setCapModal({ isOpen: true, alert: null, loading: true, copied: false });
    try {
      const alertData = await api.generateCapAlert(
        selectedEvent.id,
        { adminUsername, radiusKm: 10.0 },
        adminToken
      );
      setCapModal({ isOpen: true, alert: alertData, loading: false, copied: false });
      const alerts = await api.getCapAlerts(adminToken);
      setCapAlerts(alerts || []);
    } catch (err) {
      alert(`CAP Alert generation failed: ${err.message}`);
      setCapModal({ isOpen: false, alert: null, loading: false, copied: false });
    }
  };

  // Download XML file
  const handleDownloadXml = (xmlPayload, alertId) => {
    const blob = new Blob([xmlPayload], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cap_alert_${alertId || 'document'}.xml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Copy XML to clipboard
  const handleCopyXml = (xmlPayload) => {
    navigator.clipboard.writeText(xmlPayload);
    setCapModal(prev => ({ ...prev, copied: true }));
    setTimeout(() => setCapModal(prev => ({ ...prev, copied: false })), 2000);
  };

  // Filtered queue events
  const displayEvents = allEvents.filter(e => {
    if (queueFilter === 'triage') return e.verificationStatus === 'PENDING' || e.verificationStatus === 'SUSPICIOUS';
    if (queueFilter === 'verified') return e.verificationStatus === 'VERIFIED';
    return true;
  }).sort((a, b) => a.trustScore - b.trustScore);

  // If unauthenticated, show Token Gate
  if (!adminToken) {
    return (
      <div className="max-w-md mx-auto my-16 bg-white p-8 rounded-2xl border border-slate-200/90 shadow-card">
        <div className="flex items-center justify-center w-12 h-12 bg-blue-50 text-[#1F5B8C] rounded-xl mx-auto mb-4 border border-blue-100">
          <Lock className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-center text-[#202325] mb-1">
          Admin Verification Console
        </h2>
        <p className="text-xs text-center text-slate-500 mb-6">
          Access restricted to certified weather analysts and incident controllers.
        </p>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Admin Officer Call-sign</label>
            <input
              type="text"
              required
              value={adminUsername}
              onChange={(e) => setAdminUsername(e.target.value)}
              placeholder="e.g. officer_deshmukh"
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1F5B8C]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">X-Admin-Token Secret</label>
            <input
              type="password"
              required
              value={inputToken}
              onChange={(e) => setInputToken(e.target.value)}
              placeholder="Enter admin token..."
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1F5B8C]"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              (For prototype demo, any non-empty token string is accepted)
            </p>
          </div>

          <button
            type="submit"
            className="w-full py-2.5 px-4 rounded-lg bg-[#1F5B8C] hover:bg-[#184870] text-white font-semibold text-xs transition shadow-sm"
          >
            Authenticate & Open Console
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Mode Toggle */}
      <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-50 text-[#2E8B57] rounded-lg">
            <Unlock className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-[#202325]">Verification Operations Console</h2>
              <span className="text-[10px] font-semibold bg-blue-100 text-[#1F5B8C] px-2 py-0.5 rounded">
                Officer: {adminUsername}
              </span>
            </div>
            <p className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
              <span>Ground truth verification & emergency alert payload generation</span>
              <span className="font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200">
                Demo: Alert Generation (no real dispatch)
              </span>
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Sub-tabs */}
          <div className="flex bg-slate-100 p-1 rounded-lg">
            <button
              onClick={() => setActiveSubTab('triage')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                activeSubTab === 'triage'
                  ? 'bg-white text-[#1F5B8C] font-semibold shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Event Review Queue
            </button>

            <button
              onClick={() => setActiveSubTab('cap_history')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1 ${
                activeSubTab === 'cap_history'
                  ? 'bg-white text-[#1F5B8C] font-semibold shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Radio className="w-3.5 h-3.5 text-red-600" />
              <span>Alert History ({capAlerts.length})</span>
            </button>

            <button
              onClick={() => setActiveSubTab('audit')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1 ${
                activeSubTab === 'audit'
                  ? 'bg-white text-[#1F5B8C] font-semibold shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>Audit Log ({auditLogs.length})</span>
            </button>
          </div>

          <button
            onClick={fetchAdminData}
            title="Refresh list"
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={handleLogout}
            className="text-xs text-slate-500 hover:text-[#C1444B] px-2.5 py-1.5 rounded-md border border-slate-200 hover:border-[#C1444B]/30 transition"
          >
            Log Out
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 p-3 rounded-xl text-xs text-[#C1444B] flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Content Area */}
      {activeSubTab === 'triage' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Table */}
          <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200/90 shadow-card overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-[#202325]">Weather Incidents Queue</h3>
                <p className="text-xs text-slate-500">Sorted by trust score (ascending)</p>
              </div>

              {/* Queue Filter Dropdown */}
              <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg text-xs">
                <button
                  onClick={() => setQueueFilter('triage')}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition ${
                    queueFilter === 'triage' ? 'bg-white text-[#1F5B8C] shadow-sm' : 'text-slate-600'
                  }`}
                >
                  Triage (Pending/Suspicious)
                </button>
                <button
                  onClick={() => setQueueFilter('verified')}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition ${
                    queueFilter === 'verified' ? 'bg-white text-[#2E8B57] shadow-sm' : 'text-slate-600'
                  }`}
                >
                  Verified
                </button>
                <button
                  onClick={() => setQueueFilter('all')}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition ${
                    queueFilter === 'all' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-600'
                  }`}
                >
                  All ({allEvents.length})
                </button>
              </div>
            </div>

            <div className="overflow-x-auto max-h-[560px]">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 sticky top-0 z-10 text-slate-600 uppercase font-semibold text-[10px] tracking-wider">
                  <tr>
                    <th className="py-2.5 px-3">Trust</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Event Type</th>
                    <th className="py-2.5 px-3">Location</th>
                    <th className="py-2.5 px-3">Source</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {displayEvents.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="py-12 text-center text-slate-400">
                        No weather events matching current filter criteria.
                      </td>
                    </tr>
                  ) : (
                    displayEvents.map(event => {
                      const isSelected = selectedEvent?.id === event.id;
                      return (
                        <tr
                          key={event.id}
                          onClick={() => setSelectedEvent(event)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-blue-50/80 font-medium'
                              : 'hover:bg-slate-50'
                          }`}
                        >
                          {/* Trust Score */}
                          <td className="py-3 px-3">
                            <span className={`font-bold ${
                              event.trustScore >= 70 ? 'text-[#2E8B57]' : event.trustScore >= 40 ? 'text-[#E8A33D]' : 'text-[#C1444B]'
                            }`}>
                              {event.trustScore}%
                            </span>
                          </td>

                          {/* Verification Status */}
                          <td className="py-3 px-3">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                              event.verificationStatus === 'VERIFIED'
                                ? 'bg-[#2E8B57]/10 text-[#2E8B57] border border-[#2E8B57]/30'
                                : event.verificationStatus === 'SUSPICIOUS'
                                ? 'bg-[#C1444B]/10 text-[#C1444B] border border-[#C1444B]/20'
                                : 'bg-[#E8A33D]/10 text-[#E8A33D] border border-[#E8A33D]/20'
                            }`}>
                              {event.verificationStatus}
                            </span>
                          </td>

                          {/* Event Type */}
                          <td className="py-3 px-3 font-semibold text-slate-800">
                            {event.eventType}
                          </td>

                          {/* Location */}
                          <td className="py-3 px-3 text-slate-600 truncate max-w-[120px]">
                            {event.city || 'N/A'}, {event.state || ''}
                          </td>

                          {/* Source */}
                          <td className="py-3 px-3">
                            <span className="text-[10px] text-slate-500 font-mono">
                              {event.source}
                            </span>
                          </td>

                          {/* Arrow indicator */}
                          <td className="py-3 px-3 text-right text-slate-400">
                            <ChevronRight className="w-4 h-4 ml-auto" />
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Side Panel: Factor Breakdown, CAP Alert Generation & Override Decisions */}
          <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200/90 shadow-card p-5 flex flex-col justify-between">
            {selectedEvent ? (
              <div className="space-y-4">
                {/* Header */}
                <div className="border-b border-slate-100 pb-3 flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white px-2 py-0.5 rounded bg-[#1F5B8C]">
                        {selectedEvent.eventType}
                      </span>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                        selectedEvent.verificationStatus === 'VERIFIED'
                          ? 'bg-[#2E8B57]/10 text-[#2E8B57] border border-[#2E8B57]/30'
                          : selectedEvent.verificationStatus === 'SUSPICIOUS'
                          ? 'bg-[#C1444B]/10 text-[#C1444B]'
                          : 'bg-[#E8A33D]/10 text-[#E8A33D]'
                      }`}>
                        {selectedEvent.verificationStatus}
                      </span>
                    </div>
                    <h4 className="text-sm font-bold text-slate-900 mt-1">
                      Event ID: <span className="font-mono text-xs">{selectedEvent.id}</span>
                    </h4>
                    <p className="text-xs text-slate-500">
                      📍 {selectedEvent.city}, {selectedEvent.state} &bull; {new Date(selectedEvent.reportedAt).toLocaleString()}
                    </p>
                  </div>
                </div>

                {/* Prominent CAP Alert Generation Button when VERIFIED */}
                {selectedEvent.verificationStatus === 'VERIFIED' ? (
                  <div className="p-3 bg-gradient-to-r from-red-50 to-amber-50 rounded-xl border border-red-200/80 shadow-sm space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-800 flex items-center gap-1.5">
                        <Radio className="w-4 h-4 text-red-600 animate-pulse" />
                        OASIS CAP v1.2 Alert Standard
                      </span>
                      <span className="text-[10px] font-bold text-red-700 uppercase bg-red-100 px-1.5 py-0.5 rounded">
                        Verified Event
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600">
                      Generate a standards-compliant Common Alerting Protocol XML document ready for disaster management systems (NDMA/SACHET).
                    </p>
                    <button
                      onClick={handleGenerateCapAlert}
                      disabled={capModal.loading}
                      className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-700 hover:to-amber-700 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-sm transition transform hover:scale-[1.01] active:scale-95 disabled:opacity-50"
                    >
                      <FileText className="w-4 h-4" />
                      <span>{capModal.loading ? 'Generating CAP v1.2 XML...' : '🚨 Generate CAP Alert (v1.2 XML)'}</span>
                    </button>
                  </div>
                ) : (
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-500 flex items-center gap-2">
                    <Info className="w-4 h-4 shrink-0 text-slate-400" />
                    <span>Approve event as <b>VERIFIED</b> to enable CAP v1.2 XML alert generation.</span>
                  </div>
                )}

                {/* Raw Text */}
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                    Raw Report Text
                  </label>
                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-700 italic">
                    "{selectedEvent.rawText}"
                  </div>
                </div>

                {/* Factor Breakdown Inspection Panel */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-bold text-[#202325]">
                      Factor Breakdown Scoring
                    </label>
                    <span className="text-xs font-bold text-[#1F5B8C]">
                      Net Trust: {selectedEvent.trustScore}/100
                    </span>
                  </div>

                  <div className="space-y-2 text-xs bg-slate-50 p-3 rounded-lg border border-slate-200">
                    {/* Source Trust */}
                    <div>
                      <div className="flex justify-between text-slate-700 mb-1">
                        <span>Source Credibility ({selectedEvent.source}):</span>
                        <b>{selectedEvent.factorBreakdown?.sourceTrust ?? 50}/100</b>
                      </div>
                      <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#1F5B8C] rounded-full"
                          style={{ width: `${selectedEvent.factorBreakdown?.sourceTrust ?? 50}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* Corroboration Boost */}
                    <div>
                      <div className="flex justify-between text-slate-700 mb-1">
                        <span>Corroboration Boost ({selectedEvent.corroborationCount || 0} independent events):</span>
                        <b>+{selectedEvent.factorBreakdown?.corroborationBoost ?? 0}</b>
                      </div>
                      <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{ width: `${Math.min(100, ((selectedEvent.factorBreakdown?.corroborationBoost ?? 0) / 30) * 100)}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* Cross-Match Official IMD */}
                    <div>
                      <div className="flex justify-between text-slate-700 mb-1">
                        <span>IMD Official Reading Match:</span>
                        <b className={selectedEvent.factorBreakdown?.crossMatchOfficial < 0 ? 'text-[#C1444B]' : 'text-[#2E8B57]'}>
                          {selectedEvent.factorBreakdown?.crossMatchOfficial >= 0 ? '+' : ''}{selectedEvent.factorBreakdown?.crossMatchOfficial ?? 0}
                        </b>
                      </div>
                    </div>

                    {/* Image Check */}
                    <div>
                      <div className="flex justify-between text-slate-700 mb-1">
                        <span>Media EXIF & Timestamp Plausibility:</span>
                        <b className={selectedEvent.factorBreakdown?.imageCheck < 0 ? 'text-[#C1444B]' : 'text-slate-700'}>
                          {selectedEvent.factorBreakdown?.imageCheck >= 0 ? '+' : ''}{selectedEvent.factorBreakdown?.imageCheck ?? 0}
                        </b>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Action Buttons calling POST /admin/events/:id/override */}
                <div className="pt-3 border-t border-slate-100">
                  <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                    Override Actions (Requires X-Admin-Token)
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      onClick={() => openOverrideModal('VERIFIED')}
                      className="py-2 px-3 rounded-lg bg-[#2E8B57] hover:bg-[#257247] text-white text-xs font-semibold flex items-center justify-center gap-1 shadow-sm transition"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>Approve</span>
                    </button>

                    <button
                      onClick={() => openOverrideModal('REJECTED')}
                      className="py-2 px-3 rounded-lg bg-[#C1444B] hover:bg-[#A9393F] text-white text-xs font-semibold flex items-center justify-center gap-1 shadow-sm transition"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>

                    <button
                      onClick={() => openOverrideModal('DUPLICATE')}
                      className="py-2 px-3 rounded-lg bg-slate-700 hover:bg-slate-800 text-white text-xs font-semibold flex items-center justify-center gap-1 shadow-sm transition"
                    >
                      <Copy className="w-3.5 h-3.5" />
                      <span>Duplicate</span>
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs py-20">
                Select an alert from the queue to inspect factor breakdown.
              </div>
            )}
          </div>
        </div>
      ) : activeSubTab === 'cap_history' ? (
        /* CAP Alert History Sub-Tab */
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-card p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-[#202325]">OASIS CAP v1.2 Generated Alerts History</h3>
                <span className="text-[10px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded border border-amber-300">
                  Demo: Alert Generation (no real dispatch)
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Audit trail of Common Alerting Protocol XML emergency documents generated for disaster response systems.
              </p>
            </div>
            <button
              onClick={fetchAdminData}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1 self-start sm:self-auto transition"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Refresh History
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Sent / Generated</th>
                  <th className="py-2.5 px-3">CAP Event</th>
                  <th className="py-2.5 px-3">Headline / Area</th>
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3">Urgency</th>
                  <th className="py-2.5 px-3">Certainty</th>
                  <th className="py-2.5 px-3">Generated By</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {capAlerts.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="py-12 text-center text-slate-400">
                      No CAP v1.2 alerts have been generated yet. Select a VERIFIED event from the queue to generate one.
                    </td>
                  </tr>
                ) : (
                  capAlerts.map(alert => {
                    const isExtreme = alert.severity === 'Extreme';
                    const isSevere = alert.severity === 'Severe';

                    return (
                      <tr key={alert.id} className="hover:bg-slate-50 transition">
                        <td className="py-3 px-3 text-slate-500 font-mono text-[11px]">
                          {new Date(alert.sent || alert.generatedAt).toLocaleString()}
                        </td>
                        <td className="py-3 px-3 font-bold text-slate-900">
                          {alert.event}
                        </td>
                        <td className="py-3 px-3 text-slate-700 truncate max-w-[220px]">
                          {alert.headline}
                        </td>
                        <td className="py-3 px-3">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                            isExtreme
                              ? 'bg-[#C1444B] text-white'
                              : isSevere
                              ? 'bg-[#E8A33D] text-white'
                              : 'bg-blue-600 text-white'
                          }`}>
                            {alert.severity}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-slate-700 font-semibold">
                          {alert.urgency}
                        </td>
                        <td className="py-3 px-3 text-slate-600">
                          {alert.certainty}
                        </td>
                        <td className="py-3 px-3 font-semibold text-[#1F5B8C]">
                          {alert.generatedBy}
                        </td>
                        <td className="py-3 px-3 text-right space-x-2">
                          <button
                            onClick={() => setCapModal({ isOpen: true, alert, loading: false, copied: false })}
                            className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold transition inline-flex items-center gap-1"
                          >
                            <Code className="w-3 h-3" /> View XML
                          </button>
                          <button
                            onClick={() => handleDownloadXml(alert.xmlPayload, alert.id)}
                            className="px-2.5 py-1 bg-[#1F5B8C] hover:bg-[#184870] text-white rounded text-xs font-semibold transition inline-flex items-center gap-1"
                          >
                            <Download className="w-3 h-3" /> XML
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Audit Log View */
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-card p-5">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-[#202325]">Administrative Audit Trail</h3>
            <p className="text-xs text-slate-500">Immutable record of status overrides and verification logs</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Event ID</th>
                  <th className="py-2.5 px-3">Officer</th>
                  <th className="py-2.5 px-3">Transition</th>
                  <th className="py-2.5 px-3">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="py-12 text-center text-slate-400">
                      No administrative overrides recorded yet.
                    </td>
                  </tr>
                ) : (
                  auditLogs.map(log => (
                    <tr key={log.id} className="hover:bg-slate-50">
                      <td className="py-3 px-3 text-slate-500 font-mono text-[11px]">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="py-3 px-3 font-mono font-medium text-[#1F5B8C]">
                        {log.eventId}
                      </td>
                      <td className="py-3 px-3 font-semibold text-slate-800">
                        {log.adminUsername}
                      </td>
                      <td className="py-3 px-3">
                        <span className="text-slate-500 line-through mr-1.5">{log.oldStatus}</span>
                        &rarr;
                        <span className="font-bold text-slate-900 ml-1.5">{log.newStatus}</span>
                      </td>
                      <td className="py-3 px-3 text-slate-600 italic">
                        "{log.reason}"
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Override Reason Modal */}
      {overrideModal.isOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 shadow-elevated border border-slate-200">
            <h3 className="text-base font-bold text-slate-900 mb-1">
              Confirm Status Override to <span className="text-[#1F5B8C] font-mono">{overrideModal.newStatus}</span>
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              This action will be published to the live WebSocket feed and logged permanently in the audit trail.
            </p>

            <div className="space-y-3 mb-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Reason for Decision</label>
                <textarea
                  rows="3"
                  value={overrideModal.reason}
                  onChange={(e) => setOverrideModal(prev => ({ ...prev, reason: e.target.value }))}
                  className="w-full p-2.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1F5B8C]"
                  placeholder="State technical basis for override..."
                ></textarea>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2">
              <button
                onClick={() => setOverrideModal({ isOpen: false, newStatus: '', reason: '', duplicateOfId: '' })}
                className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                disabled={submitting}
                onClick={handleExecuteOverride}
                className="px-4 py-2 text-xs font-semibold bg-[#1F5B8C] hover:bg-[#184870] text-white rounded-lg shadow-sm transition disabled:opacity-50"
              >
                {submitting ? 'Applying...' : 'Confirm Override'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CAP Alert Viewer & Download Modal */}
      {capModal.isOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl border border-slate-200 flex flex-col max-h-[90vh]">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3 mb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-900">
                    OASIS CAP v1.2 XML Alert Document
                  </h3>
                  <span className="text-[10px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded border border-amber-300">
                    Demo: Alert Generation (no real dispatch)
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Standards-compliant emergency payload formatted per OASIS Common Alerting Protocol v1.2 specification.
                </p>
              </div>
              <button
                onClick={() => setCapModal({ isOpen: false, alert: null, loading: false, copied: false })}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition text-lg"
              >
                &times;
              </button>
            </div>

            {capModal.loading ? (
              <div className="py-20 text-center text-slate-500 text-xs">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-[#1F5B8C]" />
                Generating standards-compliant CAP v1.2 XML payload...
              </div>
            ) : capModal.alert ? (
              <div className="flex-1 overflow-y-auto space-y-4">
                {/* Alert Metadata Badges */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs">
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase block">Event</span>
                    <strong className="text-slate-900">{capModal.alert.event}</strong>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase block">Severity</span>
                    <span className={`inline-block font-bold text-[11px] px-2 py-0.2 rounded uppercase ${
                      capModal.alert.severity === 'Extreme'
                        ? 'bg-[#C1444B] text-white'
                        : capModal.alert.severity === 'Severe'
                        ? 'bg-[#E8A33D] text-white'
                        : 'bg-blue-600 text-white'
                    }`}>
                      {capModal.alert.severity}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase block">Urgency</span>
                    <strong className="text-slate-800">{capModal.alert.urgency}</strong>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase block">Certainty</span>
                    <strong className="text-slate-800">{capModal.alert.certainty}</strong>
                  </div>
                </div>

                {/* XML Code Block */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                      <Code className="w-3.5 h-3.5" /> XML Payload Structure
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      urn:oasis:names:tc:emergency:cap:1.2
                    </span>
                  </div>
                  <pre className="bg-slate-950 text-emerald-400 p-4 rounded-xl font-mono text-xs overflow-x-auto max-h-80 border border-slate-800 shadow-inner">
                    <code>{capModal.alert.xmlPayload}</code>
                  </pre>
                </div>
              </div>
            ) : null}

            {/* Modal Actions */}
            {capModal.alert && (
              <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-slate-400 italic">
                  Identifier: <span className="font-mono">{capModal.alert.identifier}</span>
                </span>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleCopyXml(capModal.alert.xmlPayload)}
                    className="px-3.5 py-2 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition flex items-center gap-1.5"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    <span>{capModal.copied ? 'Copied XML!' : 'Copy XML'}</span>
                  </button>
                  <button
                    onClick={() => handleDownloadXml(capModal.alert.xmlPayload, capModal.alert.id)}
                    className="px-4 py-2 text-xs font-semibold bg-[#1F5B8C] hover:bg-[#184870] text-white rounded-lg shadow-sm transition flex items-center gap-1.5"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download XML File</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

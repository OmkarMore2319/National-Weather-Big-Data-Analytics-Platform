import React, { useState } from 'react';
import { api } from '../services/api';
import { X, Send, MapPin, Camera } from 'lucide-react';

const CITIES = [
  { city: 'Mumbai', state: 'Maharashtra', lat: 19.0760, lon: 72.8777 },
  { city: 'Delhi', state: 'Delhi', lat: 28.6139, lon: 77.2090 },
  { city: 'Bengaluru', state: 'Karnataka', lat: 12.9716, lon: 77.5946 },
  { city: 'Kolkata', state: 'West Bengal', lat: 22.5726, lon: 88.3639 },
  { city: 'Chennai', state: 'Tamil Nadu', lat: 13.0827, lon: 80.2707 },
  { city: 'Jaipur', state: 'Rajasthan', lat: 26.9124, lon: 75.7873 },
  { city: 'Shimla', state: 'Himachal Pradesh', lat: 31.1048, lon: 77.1734 },
  { city: 'Puri', state: 'Odisha', lat: 19.8135, lon: 85.8312 }
];

export function CitizenReportModal({ isOpen, onClose, onSuccess }) {
  const [selectedCity, setSelectedCity] = useState(CITIES[0]);
  const [rawText, setRawText] = useState('');
  const [mediaUrl, setMediaUrl] = useState('');
  const [consentGiven, setConsentGiven] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!rawText.trim()) return;

    setSubmitting(true);
    try {
      await api.submitCitizenReport({
        rawText,
        mediaUrls: mediaUrl.trim() ? [mediaUrl.trim()] : [],
        lat: selectedCity.lat + (Math.random() - 0.5) * 0.04,
        lon: selectedCity.lon + (Math.random() - 0.5) * 0.04,
        city: selectedCity.city,
        state: selectedCity.state,
        consentGiven
      });

      setRawText('');
      setMediaUrl('');
      onSuccess();
      onClose();
    } catch (err) {
      alert(`Report failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-elevated border border-slate-200">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-base font-bold text-[#202325]">Submit Citizen Weather Report</h3>
            <p className="text-xs text-slate-500">POST /api/v1/reports/citizen</p>
          </div>
          <button onClick={onClose} className="p-1 rounded-md text-slate-400 hover:text-slate-700">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 mt-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">City / Location</label>
            <select
              value={selectedCity.city}
              onChange={(e) => {
                const found = CITIES.find(c => c.city === e.target.value);
                if (found) setSelectedCity(found);
              }}
              className="w-full p-2.5 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[#1F5B8C]"
            >
              {CITIES.map(c => (
                <option key={c.city} value={c.city}>{c.city}, {c.state}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Report Description (rawText)</label>
            <textarea
              required
              rows="3"
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="e.g. Heavy downpour causing severe waterlogging near railway crossing..."
              className="w-full p-2.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1F5B8C]"
            ></textarea>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Photo Evidence URL (Optional)</label>
            <input
              type="url"
              value={mediaUrl}
              onChange={(e) => setMediaUrl(e.target.value)}
              placeholder="https://images.unsplash.com/..."
              className="w-full p-2.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1F5B8C]"
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="consent"
              checked={consentGiven}
              onChange={(e) => setConsentGiven(e.target.checked)}
              className="rounded text-[#1F5B8C] focus:ring-[#1F5B8C]"
            />
            <label htmlFor="consent" className="text-slate-600 text-[11px]">
              I give consent for crowdsourced meteorological analysis under open government data guidelines.
            </label>
          </div>

          <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 font-semibold bg-[#1F5B8C] hover:bg-[#184870] text-white rounded-lg shadow-sm transition disabled:opacity-50 flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{submitting ? 'Submitting...' : 'Broadcast Report'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

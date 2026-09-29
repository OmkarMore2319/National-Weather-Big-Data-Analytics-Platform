import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Search, MapPin, X } from 'lucide-react';
import indianCitiesData from '../data/indian_cities.json';

// Event Type Color Mapping
const EVENT_COLORS = {
  RAINFALL: '#1F5B8C',      // Deep Blue
  THUNDERSTORM: '#7C3AED',  // Violet
  FLOODING: '#0D9488',      // Dark Teal
  HEATWAVE: '#D97706',      // Amber
  FOG: '#64748B',           // Cool Slate
  DUST_STORM: '#B45309',     // Warm Ochre
  STRONG_WIND: '#0284C7',   // Sky Blue
  UNKNOWN: '#94A3B8'        // Steel Grey
};

export function WeatherMap({ events, selectedEvent, onSelectEvent }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);
  const searchMarkerRef = useRef(null);

  // Map Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchError, setSearchError] = useState('');
  const [suggestions, setSuggestions] = useState([]);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      // Center on India
      const map = L.map(mapContainerRef.current, {
        center: [22.5, 79.5],
        zoom: 5,
        minZoom: 4,
        maxZoom: 14,
        scrollWheelZoom: true
      });

      // Tile layer selection: OpenStreetMap (free) or CARTO (if valid key supplied)
      const cartoApiKey = import.meta.env.VITE_CARTO_API_KEY;
      const hasValidCartoKey = cartoApiKey && cartoApiKey !== 'cb1_40ef_1_661c7d48f4c15754240e957e' && cartoApiKey.trim() !== '';

      const tileUrl = hasValidCartoKey
        ? `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?api_key=${cartoApiKey}`
        : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

      L.tileLayer(tileUrl, {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' + (hasValidCartoKey ? ' &copy; <a href="https://carto.com/attributions">CARTO</a>' : ''),
        subdomains: hasValidCartoKey ? 'abcd' : 'abc',
        maxZoom: 19
      }).addTo(map);

      markersLayerRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;
    }

    return () => {
      // Cleanup on unmount
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Event Markers when events change
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;

    const layer = markersLayerRef.current;
    layer.clearLayers();

    const pointsToRender = events.slice(0, 200);

    pointsToRender.forEach(event => {
      if (!event.lat || !event.lon) return;

      const bg = EVENT_COLORS[event.eventType] || EVENT_COLORS.UNKNOWN;
      let statusClass = 'marker-verified';

      if (event.verificationStatus === 'PENDING') {
        statusClass = 'marker-pending';
      } else if (event.verificationStatus === 'SUSPICIOUS') {
        statusClass = 'marker-suspicious'; // Red outline (ONLY red on dashboard!)
      } else if (event.verificationStatus === 'DUPLICATE') {
        statusClass = 'marker-duplicate';
      }

      // Check if this is a live newly arrived report
      const isVeryRecent = (Date.now() - new Date(event.reportedAt || event.ingestedAt).getTime()) < 60000;
      const pulseClass = isVeryRecent ? 'live-pulse' : '';

      const isReddit = event.source === 'SOCIAL_REAL' || event.sourceMeta?.platform === 'reddit' || event.sourceMeta?.subSource === 'reddit';
      const isSimulated = !isReddit && (event.source === 'SOCIAL_SIMULATED' || event.sourceMeta?.simulated);

      // Create Custom HTML Div Icon
      const customIcon = L.divIcon({
        className: 'custom-weather-marker',
        html: `
          <div class="relative flex items-center justify-center">
            <div class="w-8 h-8 rounded-full flex items-center justify-center shadow-md ${statusClass} ${pulseClass}" style="background-color: ${bg}; color: white; font-weight: 700; font-size: 11px;">
              ${event.eventType.charAt(0)}
            </div>
            ${isReddit ? `
              <span class="absolute -top-1 -right-1 flex h-3 w-3">
                <span class="relative inline-flex rounded-full h-3 w-3 bg-indigo-600 border border-white"></span>
              </span>
            ` : isSimulated ? `
              <span class="absolute -top-1 -right-1 flex h-3 w-3">
                <span class="relative inline-flex rounded-full h-3 w-3 bg-purple-600 border border-white"></span>
              </span>
            ` : ''}
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
        popupAnchor: [0, -16]
      });

      const marker = L.marker([event.lat, event.lon], { icon: customIcon });

      // Build Rich HTML Popup
      const fb = event.factorBreakdown || { sourceTrust: 50, corroborationBoost: 0, crossMatchOfficial: 0, imageCheck: 0 };
      const mediaHtml = (event.mediaUrls && event.mediaUrls.length > 0)
        ? `<div class="mt-2.5 rounded-lg overflow-hidden border border-slate-200 h-28 bg-slate-100">
             <img src="${event.mediaUrls[0]}" alt="Event Evidence" class="w-full h-full object-cover" onerror="this.style.display='none'"/>
           </div>`
        : '';

      const popupHtml = `
        <div class="p-3.5 max-w-[280px] font-sans">
          <!-- Header: Type & Social Badges -->
          <div class="flex items-center justify-between gap-2 mb-1.5">
            <span class="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded text-white" style="background-color: ${bg}">
              ${event.eventType}
            </span>
            <div class="flex items-center gap-1">
              ${isReddit ? `
                <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">
                  (Reddit)
                </span>
              ` : isSimulated ? `
                <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 border border-purple-200">
                  (Simulated Feed)
                </span>
              ` : `
                <span class="text-[10px] font-semibold text-slate-500 uppercase">
                  ${event.source}
                </span>
              `}
            </div>
          </div>

          <!-- Location & Time -->
          <div class="text-xs font-semibold text-slate-800 flex items-center gap-1">
            📍 ${event.city ? event.city + ', ' : ''}${event.state || 'India'}
          </div>
          <div class="text-[11px] text-slate-400 mb-2">
            ${new Date(event.reportedAt || event.ingestedAt).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
          </div>

          <!-- Raw Text -->
          <p class="text-xs text-slate-600 italic bg-slate-50 p-2 rounded border border-slate-100 line-clamp-3 mb-2.5">
            "${event.rawText || 'No text provided.'}"
          </p>

          ${mediaHtml}

          <!-- Trust Score Gauge -->
          <div class="mt-2.5 pt-2.5 border-t border-slate-100">
            <div class="flex items-center justify-between text-xs mb-1">
              <span class="font-bold text-slate-700">Trust Score:</span>
              <span class="font-bold ${event.trustScore >= 70 ? 'text-[#2E8B57]' : event.trustScore >= 40 ? 'text-[#E8A33D]' : 'text-[#C1444B]'}">
                ${event.trustScore}/100 (${event.verificationStatus})
              </span>
            </div>
            <div class="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all" style="width: ${event.trustScore}%; background-color: ${event.trustScore >= 70 ? '#2E8B57' : event.trustScore >= 40 ? '#E8A33D' : '#C1444B'};"></div>
            </div>

            <!-- Factor Breakdown Badges -->
            <div class="grid grid-cols-2 gap-1 mt-2 text-[10px]">
              <div class="bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">Source: <b>${fb.sourceTrust}</b></div>
              <div class="bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">Corrob: <b>+${fb.corroborationBoost}</b></div>
              <div class="bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">IMD Match: <b>${fb.crossMatchOfficial >= 0 ? '+' : ''}${fb.crossMatchOfficial}</b></div>
              <div class="bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">Image: <b>${fb.imageCheck >= 0 ? '+' : ''}${fb.imageCheck}</b></div>
            </div>
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml);
      marker.on('click', () => {
        if (onSelectEvent) onSelectEvent(event);
      });

      layer.addLayer(marker);
    });

    // If an event is selected from list, pan to it
    if (selectedEvent && selectedEvent.lat && selectedEvent.lon) {
      mapInstanceRef.current.setView([selectedEvent.lat, selectedEvent.lon], 9, { animate: true });
    }
  }, [events, selectedEvent, onSelectEvent]);

  // Handle Search Input Change & Autocomplete Suggestions
  const handleSearchChange = (val) => {
    setSearchQuery(val);
    setSearchError('');

    if (!val || val.trim().length === 0) {
      setSuggestions([]);
      return;
    }

    const q = val.trim().toLowerCase();
    const matches = indianCitiesData.cities.filter(c => {
      if (c.city.toLowerCase().includes(q)) return true;
      if (c.state && c.state.toLowerCase().includes(q)) return true;
      if (c.aliases && c.aliases.some(a => a.toLowerCase().includes(q))) return true;
      return false;
    }).slice(0, 6);

    setSuggestions(matches);
  };

  // Perform Location Search Zoom & Marker Drop
  const performSearch = (targetCityObj = null) => {
    setSuggestions([]);
    const query = (targetCityObj?.city || searchQuery).trim();

    if (!query) return;

    let matched = targetCityObj;
    if (!matched) {
      const qLower = query.toLowerCase();
      matched = indianCitiesData.cities.find(c =>
        c.city.toLowerCase() === qLower ||
        c.city.toLowerCase().startsWith(qLower) ||
        (c.aliases && c.aliases.some(a => a.toLowerCase() === qLower))
      ) || indianCitiesData.cities.find(c =>
        c.city.toLowerCase().includes(qLower)
      );
    }

    if (!matched) {
      setSearchError('Location not found');
      return;
    }

    setSearchError('');
    setSearchQuery(matched.city);

    if (!mapInstanceRef.current) return;

    // Remove previous search marker if present
    if (searchMarkerRef.current) {
      mapInstanceRef.current.removeLayer(searchMarkerRef.current);
      searchMarkerRef.current = null;
    }

    // Pan map to searched city
    mapInstanceRef.current.flyTo([matched.lat, matched.lon], 10, { animate: true, duration: 1.2 });

    // Check if any existing events exist near this location
    const nearbyEvents = events.filter(e => {
      if (e.city && e.city.toLowerCase() === matched.city.toLowerCase()) return true;
      if (e.lat && e.lon) {
        return Math.abs(e.lat - matched.lat) < 0.3 && Math.abs(e.lon - matched.lon) < 0.3;
      }
      return false;
    });

    // Create custom search marker pin
    const searchPinIcon = L.divIcon({
      className: 'custom-search-pin',
      html: `
        <div class="relative flex items-center justify-center">
          <div class="w-9 h-9 rounded-full bg-[#1F5B8C] border-2 border-white shadow-xl flex items-center justify-center text-white">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </div>
        </div>
      `,
      iconSize: [36, 36],
      iconAnchor: [18, 36],
      popupAnchor: [0, -36]
    });

    const marker = L.marker([matched.lat, matched.lon], { icon: searchPinIcon });

    const tooltipContent = nearbyEvents.length === 0
      ? `<div class="p-2.5 font-sans max-w-[220px]">
           <div class="text-xs font-bold text-slate-800 mb-1 flex items-center gap-1">📍 ${matched.city}, ${matched.state}</div>
           <div class="text-xs text-slate-600 bg-slate-100 p-2 rounded border border-slate-200">
             No reports for ${matched.city} in the active window yet
           </div>
         </div>`
      : `<div class="p-2.5 font-sans max-w-[230px]">
           <div class="text-xs font-bold text-slate-800 mb-1 flex items-center gap-1">📍 ${matched.city}, ${matched.state}</div>
           <div class="text-xs text-emerald-800 bg-emerald-50 p-2 rounded border border-emerald-200 font-medium">
             ${nearbyEvents.length} active weather report(s) found in this city
           </div>
         </div>`;

    marker.bindPopup(tooltipContent);
    marker.addTo(mapInstanceRef.current);
    marker.openPopup();
    searchMarkerRef.current = marker;
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchError('');
    setSuggestions([]);
    if (searchMarkerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(searchMarkerRef.current);
      searchMarkerRef.current = null;
    }
  };

  return (
    <div className="relative w-full h-[520px] rounded-xl overflow-hidden border border-slate-200/90 shadow-card bg-slate-100">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Map Location Search Box Overlay */}
      <div className="absolute top-3 left-3 z-[1000] w-72 bg-white/95 backdrop-blur-md p-2.5 rounded-xl border border-slate-200/90 shadow-lg">
        <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1">
          <MapPin className="w-3.5 h-3.5 text-[#1F5B8C]" />
          <span>Search Map Location</span>
        </div>
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search any location..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && performSearch()}
            className="w-full pl-8 pr-7 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#1F5B8C]/30 focus:border-[#1F5B8C] font-medium bg-white"
          />
          {searchQuery && (
            <button
              onClick={handleClearSearch}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {searchError && (
          <div className="mt-1.5 text-[11px] text-[#C1444B] font-semibold px-1">
            {searchError}
          </div>
        )}

        {/* Suggestions Dropdown */}
        {suggestions.length > 0 && (
          <div className="mt-1 bg-white border border-slate-200 rounded-lg shadow-xl max-h-44 overflow-y-auto divide-y divide-slate-100">
            {suggestions.map(s => (
              <div
                key={`${s.city}-${s.state}`}
                onClick={() => performSearch(s)}
                className="p-2 text-xs hover:bg-blue-50/70 cursor-pointer flex items-center justify-between font-medium text-slate-700"
              >
                <span>{s.city}</span>
                <span className="text-[10px] text-slate-400">{s.state}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-3 left-3 z-[1000] bg-white/95 backdrop-blur-sm p-3 rounded-lg border border-slate-200/80 shadow-md text-xs space-y-1.5 max-w-[210px]">
        <div className="font-bold text-slate-800 text-[11px] uppercase tracking-wider pb-1 border-b border-slate-100">
          Status Code Border:
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-slate-200 border-2 border-[#2E8B57]"></span>
          <span className="text-slate-700">Solid: <b>VERIFIED</b></span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-slate-200 border-2 border-dashed border-[#E8A33D]"></span>
          <span className="text-slate-700">Dashed: <b>PENDING</b></span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-slate-200 border-2 border-[#C1444B] animate-pulse"></span>
          <span className="text-slate-700">Red: <b>SUSPICIOUS</b></span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-slate-300 opacity-50 border border-slate-400"></span>
          <span className="text-slate-500">Muted: <b>DUPLICATE</b></span>
        </div>
      </div>
    </div>
  );
}

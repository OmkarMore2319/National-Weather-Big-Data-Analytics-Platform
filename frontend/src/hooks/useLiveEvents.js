import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8010/ws/live';

export function useLiveEvents(filters = {}) {
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('connecting'); // 'connected', 'fallback-polling', 'connecting'
  const [newEventsToast, setNewEventsToast] = useState(null);
  const [anomalyToast, setAnomalyToast] = useState(null);

  const wsRef = useRef(null);
  const pollingIntervalRef = useRef(null);
  const filtersRef = useRef(filters);

  filtersRef.current = filters;

  // Fetch initial events, analytics summary, and anomalies
  const fetchAllData = useCallback(async (isSilent = false) => {
    try {
      if (!isSilent) setLoading(true);
      const [eventsData, summaryData, anomaliesData] = await Promise.all([
        api.getEvents(filtersRef.current),
        api.getAnalyticsSummary(),
        api.getAnomalies()
      ]);
      setEvents(eventsData);
      setSummary(summaryData);
      setAnomalies(anomaliesData || []);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to fetch weather events');
    } finally {
      if (!isSilent) setLoading(false);
    }
  }, []);

  // Handle incoming event from WebSocket
  const handleIncomingEvent = useCallback((incoming) => {
    if (!incoming || !incoming.id) return;

    setEvents(prev => {
      // Check if event already exists
      const existsIndex = prev.findIndex(e => e.id === incoming.id);
      if (existsIndex !== -1) {
        // Update in-place
        const updated = [...prev];
        updated[existsIndex] = { ...updated[existsIndex], ...incoming };
        return updated;
      }
      // Prepend newly arrived event
      return [incoming, ...prev];
    });

    // Refresh summary & anomalies
    api.getAnalyticsSummary().then(setSummary).catch(() => {});
    api.getAnomalies().then(setAnomalies).catch(() => {});

    // Trigger toast notification
    setNewEventsToast({
      type: 'event',
      id: incoming.id,
      eventType: incoming.eventType,
      city: incoming.city,
      state: incoming.state,
      source: incoming.source,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    });
  }, []);

  // Handle incoming anomaly signal from WebSocket
  const handleIncomingAnomaly = useCallback((anomalyPayload) => {
    if (!anomalyPayload) return;

    // Refresh anomalies list immediately to update badge/banner
    api.getAnomalies().then(setAnomalies).catch(() => {});

    // Format event type nicely
    const rawType = anomalyPayload.eventType || 'Weather';
    const formattedType = rawType.charAt(0).toUpperCase() + rawType.slice(1).toLowerCase().replace('_', ' ');

    setAnomalyToast({
      type: 'anomaly',
      id: `anomaly-${anomalyPayload.city}-${anomalyPayload.eventType}-${Date.now()}`,
      city: anomalyPayload.city,
      state: anomalyPayload.state,
      eventType: anomalyPayload.eventType,
      formattedType: formattedType,
      reportCount: anomalyPayload.reportCount,
      severity: anomalyPayload.severity,
      message: `🔺 New anomaly: ${formattedType} spike in ${anomalyPayload.city}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    });
  }, []);

  // Polling fallback setup
  const startPollingFallback = useCallback(() => {
    if (pollingIntervalRef.current) return;
    console.log('[Connection] Falling back to silent 10s polling for /events...');
    setConnectionStatus('fallback-polling');
    pollingIntervalRef.current = setInterval(() => {
      fetchAllData(true);
    }, 10000); // 10s per contract
  }, [fetchAllData]);

  const stopPollingFallback = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  // Setup WebSocket connection with automatic fallback to polling
  useEffect(() => {
    let reconnectTimeout = null;

    function connectWs() {
      try {
        console.log('[WebSocket] Connecting to:', WS_URL);
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('[WebSocket] Connected');
          setConnectionStatus('connected');
          stopPollingFallback();
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'event') {
              handleIncomingEvent(data.payload);
            } else if (data.type === 'anomaly') {
              handleIncomingAnomaly(data.payload);
            } else if (data.id) {
              // Legacy direct WeatherEvent fallback
              handleIncomingEvent(data);
            }
          } catch (e) {
            console.warn('[WebSocket] Malformed message:', event.data);
          }
        };

        ws.onerror = (err) => {
          console.warn('[WebSocket] Connection error:', err);
          startPollingFallback();
        };

        ws.onclose = () => {
          console.log('[WebSocket] Closed. Activating polling fallback & retrying WS in 15s...');
          startPollingFallback();
          reconnectTimeout = setTimeout(connectWs, 15000);
        };
      } catch (err) {
        console.warn('[WebSocket] Initialization failed:', err);
        startPollingFallback();
      }
    }

    connectWs();
    fetchAllData();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      stopPollingFallback();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [fetchAllData, handleIncomingEvent, handleIncomingAnomaly, startPollingFallback, stopPollingFallback]);

  // Refetch when filters change
  useEffect(() => {
    fetchAllData();
  }, [filters.eventType, filters.status, filters.city, filters.state, filters.from, filters.to, fetchAllData]);

  const dismissToast = () => setNewEventsToast(null);
  const dismissAnomalyToast = () => setAnomalyToast(null);

  return {
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
    refreshData: fetchAllData,
    setEvents
  };
}

/**
 * API Service for National Weather Big Data Analytics Platform (PS 26069)
 * Consumes the API Contract exactly with camelCase fields.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8010';

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}: ${res.statusText}`;
      try {
        const body = await res.json();
        if (body.error || body.message) {
          errorMsg = body.error || body.message;
        }
      } catch (_) {}
      throw new Error(errorMsg);
    }
    return await res.json();
  } catch (err) {
    console.error(`[API Error] ${options.method || 'GET'} ${endpoint}:`, err.message);
    throw err;
  }
}

export const api = {
  // GET /api/v1/events?eventType=&state=&city=&status=&from=&to=&page=
  getEvents: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.eventType) query.append('eventType', params.eventType);
    if (params.state) query.append('state', params.state);
    if (params.city) query.append('city', params.city);
    if (params.status) query.append('status', params.status);
    if (params.from) query.append('from', params.from);
    if (params.to) query.append('to', params.to);
    if (params.page) query.append('page', params.page);

    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/v1/events${qs}`);
  },

  // GET /api/v1/events/:id
  getEventById: async (id) => {
    return request(`/api/v1/events/${id}`);
  },

  // GET /api/v1/analytics/summary
  getAnalyticsSummary: async () => {
    return request('/api/v1/analytics/summary');
  },

  // POST /api/v1/admin/events/:id/override
  submitAdminOverride: async (id, { adminUsername, newStatus, reason }, adminToken) => {
    return request(`/api/v1/admin/events/${id}/override`, {
      method: 'POST',
      headers: {
        'X-Admin-Token': adminToken
      },
      body: JSON.stringify({ adminUsername, newStatus, reason })
    });
  },

  // GET /api/v1/admin/audit-log
  getAdminAuditLog: async (adminToken) => {
    return request('/api/v1/admin/audit-log', {
      headers: adminToken ? { 'X-Admin-Token': adminToken } : {}
    });
  },

  // POST /api/v1/reports/citizen
  submitCitizenReport: async (report) => {
    return request('/api/v1/reports/citizen', {
      method: 'POST',
      body: JSON.stringify(report)
    });
  },

  // GET /api/v1/analytics/anomalies
  getAnomalies: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.windowHours) query.append('windowHours', params.windowHours);
    if (params.threshold) query.append('threshold', params.threshold);

    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/v1/analytics/anomalies${qs}`);
  },

  // POST /api/v1/admin/events/:id/generate-alert
  generateCapAlert: async (eventId, { adminUsername, radiusKm } = {}, adminToken) => {
    return request(`/api/v1/admin/events/${eventId}/generate-alert`, {
      method: 'POST',
      headers: {
        'X-Admin-Token': adminToken
      },
      body: JSON.stringify({
        adminUsername: adminUsername || 'admin_officer',
        radiusKm: radiusKm || 10.0
      })
    });
  },

  // GET /api/v1/admin/alerts
  getCapAlerts: async (adminToken) => {
    return request('/api/v1/admin/alerts', {
      headers: adminToken ? { 'X-Admin-Token': adminToken } : {}
    });
  },

  // GET download URL for CAP alert XML
  getCapAlertXmlUrl: (alertId) => {
    return `${API_BASE_URL}/api/v1/admin/alerts/${alertId}/xml`;
  }
};

import express from 'express';
import cors from 'cors';
import { createServer } from 'http';
import { WebSocketServer, WebSocket } from 'ws';

const app = express();
const PORT = process.env.PORT || 8000;
const server = createServer(app);
const wss = new WebSocketServer({ server, path: '/ws/live' });

app.use(cors());
app.use(express.json());

// In-memory Mock Database
let events = [
  {
    id: "evt-001",
    source: "OFFICIAL_STATION",
    rawText: "Continuous torrential rainfall recorded at Colaba coastal observatory. Rain gauge: 64.2mm in 3h.",
    mediaUrls: ["https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=600"],
    reportedAt: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 24 * 60 * 1000).toISOString(),
    lat: 18.9067,
    lon: 72.8147,
    city: "Mumbai",
    state: "Maharashtra",
    eventType: "RAINFALL",
    classificationConfidence: 0.98,
    verificationStatus: "VERIFIED",
    trustScore: 95,
    factorBreakdown: { sourceTrust: 100, corroborationBoost: 15, crossMatchOfficial: 15, imageCheck: 10 },
    corroborationCount: 3,
    duplicateOfId: null,
    sourceMeta: {}
  },
  {
    id: "evt-002",
    source: "CITIZEN",
    rawText: "Waterlogging at Hindmata cinema junction, Dadar East. Knee-deep flood water on roads, bus traffic diverted.",
    mediaUrls: ["https://images.unsplash.com/photo-1547683905-f686c993aae5?w=600"],
    reportedAt: new Date(Date.now() - 40 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 38 * 60 * 1000).toISOString(),
    lat: 19.0178,
    lon: 72.8478,
    city: "Mumbai",
    state: "Maharashtra",
    eventType: "FLOODING",
    classificationConfidence: 0.96,
    verificationStatus: "VERIFIED",
    trustScore: 85,
    factorBreakdown: { sourceTrust: 50, corroborationBoost: 20, crossMatchOfficial: 15, imageCheck: 10 },
    corroborationCount: 4,
    duplicateOfId: null,
    sourceMeta: {}
  },
  {
    id: "evt-003",
    source: "NEWS_RSS",
    rawText: "Severe thunderstorm and frequent cloud-to-ground lightning reported across Salt Lake and New Town.",
    mediaUrls: [],
    reportedAt: new Date(Date.now() - 55 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 50 * 60 * 1000).toISOString(),
    lat: 22.5867,
    lon: 88.4178,
    city: "Kolkata",
    state: "West Bengal",
    eventType: "THUNDERSTORM",
    classificationConfidence: 0.91,
    verificationStatus: "VERIFIED",
    trustScore: 78,
    factorBreakdown: { sourceTrust: 75, corroborationBoost: 10, crossMatchOfficial: 15, imageCheck: 0 },
    corroborationCount: 2,
    duplicateOfId: null,
    sourceMeta: {}
  },
  {
    id: "evt-004",
    source: "SOCIAL_SIMULATED",
    rawText: "Delhi heat is unbearable today! Blistering sun and loo winds, thermometer at 46.5°C in Najafgarh.",
    mediaUrls: [],
    reportedAt: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 14 * 60 * 1000).toISOString(),
    lat: 28.6139,
    lon: 77.0190,
    city: "Delhi",
    state: "Delhi",
    eventType: "HEATWAVE",
    classificationConfidence: 0.89,
    verificationStatus: "PENDING",
    trustScore: 55,
    factorBreakdown: { sourceTrust: 40, corroborationBoost: 0, crossMatchOfficial: 15, imageCheck: 0 },
    corroborationCount: 0,
    duplicateOfId: null,
    sourceMeta: { simulated: true }
  },
  {
    id: "evt-005",
    source: "CITIZEN",
    rawText: "Dense fog blanket covers Yamuna Expressway near Greater Noida. Zero visibility, vehicles moving at 20 km/h.",
    mediaUrls: ["https://images.unsplash.com/photo-1485236715568-ddc5ee6ca227?w=600"],
    reportedAt: new Date(Date.now() - 120 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 118 * 60 * 1000).toISOString(),
    lat: 28.4744,
    lon: 77.5040,
    city: "Greater Noida",
    state: "Uttar Pradesh",
    eventType: "FOG",
    classificationConfidence: 0.94,
    verificationStatus: "PENDING",
    trustScore: 55,
    factorBreakdown: { sourceTrust: 50, corroborationBoost: 5, crossMatchOfficial: 15, imageCheck: -10 },
    corroborationCount: 1,
    duplicateOfId: null,
    sourceMeta: {}
  },
  {
    id: "evt-006",
    source: "CITIZEN",
    rawText: "Massive sandstorm and dust gale swept into Jodhpur city, sky turned orange, visibility below 50m.",
    mediaUrls: ["https://images.unsplash.com/photo-1545153996-e01b50d6f28b?w=600"],
    reportedAt: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    lat: 26.2389,
    lon: 73.0243,
    city: "Jodhpur",
    state: "Rajasthan",
    eventType: "DUST_STORM",
    classificationConfidence: 0.93,
    verificationStatus: "VERIFIED",
    trustScore: 80,
    factorBreakdown: { sourceTrust: 50, corroborationBoost: 5, crossMatchOfficial: 15, imageCheck: 10 },
    corroborationCount: 1,
    duplicateOfId: null,
    sourceMeta: {}
  },
  {
    id: "evt-007",
    source: "CITIZEN",
    rawText: "Cyclonic gale force winds gusting over 90 km/h tearing down billboards and branches along Puri beach.",
    mediaUrls: [],
    reportedAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
    lat: 19.8135,
    lon: 85.8312,
    city: "Puri",
    state: "Odisha",
    eventType: "STRONG_WIND",
    classificationConfidence: 0.92,
    verificationStatus: "VERIFIED",
    trustScore: 70,
    factorBreakdown: { sourceTrust: 50, corroborationBoost: 5, crossMatchOfficial: 15, imageCheck: 0 },
    corroborationCount: 1,
    duplicateOfId: null,
    sourceMeta: {}
  },
  {
    id: "evt-008",
    source: "SOCIAL_SIMULATED",
    rawText: "Unbearable 50 degree heatwave scorching Shimla mall road right now!",
    mediaUrls: [],
    reportedAt: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 58 * 60 * 1000).toISOString(),
    lat: 31.1048,
    lon: 77.1734,
    city: "Shimla",
    state: "Himachal Pradesh",
    eventType: "HEATWAVE",
    classificationConfidence: 0.88,
    verificationStatus: "SUSPICIOUS",
    trustScore: 0,
    factorBreakdown: { sourceTrust: 40, corroborationBoost: 0, crossMatchOfficial: -40, imageCheck: 0 },
    corroborationCount: 0,
    duplicateOfId: null,
    sourceMeta: { simulated: true }
  },
  {
    id: "evt-009",
    source: "CITIZEN",
    rawText: "Waterlogging at Hindmata cinema junction, Dadar East. Knee deep flood waters.",
    mediaUrls: [],
    reportedAt: new Date(Date.now() - 20 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 19 * 60 * 1000).toISOString(),
    lat: 19.0178,
    lon: 72.8478,
    city: "Mumbai",
    state: "Maharashtra",
    eventType: "FLOODING",
    classificationConfidence: 0.95,
    verificationStatus: "DUPLICATE",
    trustScore: 75,
    factorBreakdown: { sourceTrust: 50, corroborationBoost: 15, crossMatchOfficial: 15, imageCheck: 0 },
    corroborationCount: 3,
    duplicateOfId: "evt-002",
    sourceMeta: {}
  },
  {
    id: "evt-010",
    source: "CITIZEN",
    rawText: "Violent windstorm blowing off roofs in Pune outskirts, trees fallen.",
    mediaUrls: [],
    reportedAt: new Date(Date.now() - 75 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 70 * 60 * 1000).toISOString(),
    lat: 18.5204,
    lon: 73.8567,
    city: "Pune",
    state: "Maharashtra",
    eventType: "STRONG_WIND",
    classificationConfidence: 0.91,
    verificationStatus: "SUSPICIOUS",
    trustScore: 10,
    factorBreakdown: { sourceTrust: 50, corroborationBoost: 0, crossMatchOfficial: -40, imageCheck: 0 },
    corroborationCount: 0,
    duplicateOfId: null,
    sourceMeta: {}
  },
  {
    id: "evt-011",
    source: "CITIZEN",
    rawText: "Heavy rain in Indiranagar, water stagnation outside metro station.",
    mediaUrls: ["https://images.unsplash.com/photo-1519692933481-e162a57d6721?w=600"],
    reportedAt: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 88 * 60 * 1000).toISOString(),
    lat: 12.9784,
    lon: 77.6408,
    city: "Bengaluru",
    state: "Karnataka",
    eventType: "RAINFALL",
    classificationConfidence: 0.94,
    verificationStatus: "VERIFIED",
    trustScore: 75,
    factorBreakdown: { sourceTrust: 50, corroborationBoost: 0, crossMatchOfficial: 15, imageCheck: 10 },
    corroborationCount: 0,
    duplicateOfId: null,
    sourceMeta: {}
  },
  {
    id: "evt-012",
    source: "CITIZEN",
    rawText: "Lightning struck an electric transformer near Anna Nagar roundtana.",
    mediaUrls: [],
    reportedAt: new Date(Date.now() - 110 * 60 * 1000).toISOString(),
    ingestedAt: new Date(Date.now() - 105 * 60 * 1000).toISOString(),
    lat: 13.0850,
    lon: 80.2100,
    city: "Chennai",
    state: "Tamil Nadu",
    eventType: "THUNDERSTORM",
    classificationConfidence: 0.92,
    verificationStatus: "PENDING",
    trustScore: 65,
    factorBreakdown: { sourceTrust: 50, corroborationBoost: 0, crossMatchOfficial: 15, imageCheck: 0 },
    corroborationCount: 0,
    duplicateOfId: null,
    sourceMeta: {}
  }
];

let auditLogs = [
  {
    id: "audit-001",
    eventId: "evt-008",
    adminUsername: "officer_rajesh",
    oldStatus: "PENDING",
    newStatus: "SUSPICIOUS",
    reason: "Contradicts IMD station readings; cold weather in Shimla",
    timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString()
  }
];

// Helper to broadcast WS messages
function broadcast(data) {
  const payload = JSON.stringify(data);
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(payload);
    }
  });
}

// 1. GET /api/v1/events
app.get('/api/v1/events', (req, res) => {
  let filtered = [...events];
  const { eventType, state, city, status, from, to } = req.query;

  if (eventType) {
    const types = eventType.split(',').map(t => t.trim().toUpperCase());
    filtered = filtered.filter(e => types.includes(e.eventType));
  }
  if (state) {
    filtered = filtered.filter(e => e.state.toLowerCase() === state.toLowerCase());
  }
  if (city) {
    filtered = filtered.filter(e => e.city.toLowerCase().includes(city.toLowerCase()));
  }
  if (status) {
    const statuses = status.split(',').map(s => s.trim().toUpperCase());
    filtered = filtered.filter(e => statuses.includes(e.verificationStatus));
  }
  if (from) {
    const fromTime = new Date(from).getTime();
    filtered = filtered.filter(e => new Date(e.reportedAt).getTime() >= fromTime);
  }
  if (to) {
    const toTime = new Date(to).getTime();
    filtered = filtered.filter(e => new Date(e.reportedAt).getTime() <= toTime);
  }

  // Sort descending by reportedAt
  filtered.sort((a, b) => new Date(b.reportedAt) - new Date(a.reportedAt));
  res.json(filtered);
});

// 2. GET /api/v1/events/:id
app.get('/api/v1/events/:id', (req, res) => {
  const event = events.find(e => e.id === req.params.id);
  if (!event) {
    return res.status(404).json({ error: "Event not found" });
  }
  res.json(event);
});

// 3. GET /api/v1/analytics/summary
app.get('/api/v1/analytics/summary', (req, res) => {
  const totalToday = events.length;
  const verifiedCount = events.filter(e => e.verificationStatus === 'VERIFIED').length;
  const pctVerified = totalToday > 0 ? Math.round((verifiedCount / totalToday) * 100) : 0;

  // Breakdown by eventType
  const byEventType = {};
  const stateCounts = {};
  events.forEach(e => {
    byEventType[e.eventType] = (byEventType[e.eventType] || 0) + 1;
    stateCounts[e.state] = (stateCounts[e.state] || 0) + 1;
  });

  // Top event type
  let topEventType = "RAINFALL";
  let maxEventCount = 0;
  Object.entries(byEventType).forEach(([type, count]) => {
    if (count > maxEventCount) {
      maxEventCount = count;
      topEventType = type;
    }
  });

  // Most affected state
  let mostAffectedState = "Maharashtra";
  let maxStateCount = 0;
  Object.entries(stateCounts).forEach(([st, count]) => {
    if (count > maxStateCount) {
      maxStateCount = count;
      mostAffectedState = st;
    }
  });

  // Breakdown by status
  const byStatus = {
    VERIFIED: events.filter(e => e.verificationStatus === 'VERIFIED').length,
    PENDING: events.filter(e => e.verificationStatus === 'PENDING').length,
    SUSPICIOUS: events.filter(e => e.verificationStatus === 'SUSPICIOUS').length,
    DUPLICATE: events.filter(e => e.verificationStatus === 'DUPLICATE').length,
  };

  res.json({
    totalToday,
    pctVerified,
    topEventType,
    mostAffectedState,
    byEventType,
    byStatus
  });
});

// 4. POST /api/v1/admin/events/:id/override
app.post('/api/v1/admin/events/:id/override', (req, res) => {
  const token = req.headers['x-admin-token'];
  if (!token) {
    return res.status(401).json({ error: "Unauthorized: Missing X-Admin-Token header" });
  }

  const { adminUsername, newStatus, reason } = req.body;
  if (!adminUsername || !newStatus || !reason) {
    return res.status(400).json({ error: "Missing adminUsername, newStatus, or reason" });
  }

  const eventIndex = events.findIndex(e => e.id === req.params.id);
  if (eventIndex === -1) {
    return res.status(404).json({ error: "Event not found" });
  }

  const oldStatus = events[eventIndex].verificationStatus;
  events[eventIndex].verificationStatus = newStatus;

  const override = {
    id: `audit-${Date.now()}`,
    eventId: req.params.id,
    adminUsername,
    oldStatus,
    newStatus,
    reason,
    timestamp: new Date().toISOString()
  };

  auditLogs.unshift(override);
  broadcast(events[eventIndex]); // Broadcast update on WebSocket
  res.json(override);
});

// 5. GET /api/v1/admin/audit-log
app.get('/api/v1/admin/audit-log', (req, res) => {
  res.json(auditLogs);
});

// 6. POST /api/v1/reports/citizen
app.post('/api/v1/reports/citizen', (req, res) => {
  const { rawText, mediaUrls, lat, lon, city, state } = req.body;
  const newEvent = {
    id: `evt-${Date.now()}`,
    source: "CITIZEN",
    rawText: rawText || "Citizen weather report",
    mediaUrls: mediaUrls || [],
    reportedAt: new Date().toISOString(),
    ingestedAt: new Date().toISOString(),
    lat: lat || 19.0760,
    lon: lon || 72.8777,
    city: city || "Mumbai",
    state: state || "Maharashtra",
    eventType: "RAINFALL",
    classificationConfidence: 0.85,
    verificationStatus: "PENDING",
    trustScore: 50,
    factorBreakdown: { sourceTrust: 50, corroborationBoost: 0, crossMatchOfficial: 0, imageCheck: 0 },
    corroborationCount: 0,
    duplicateOfId: null,
    sourceMeta: {}
  };
  events.unshift(newEvent);
  broadcast(newEvent);
  res.status(201).json(newEvent);
});

// Periodic mock WebSocket event emitter to test live animations and toast
const SIMULATED_CITIES = [
  { city: "Hyderabad", state: "Telangana", lat: 17.3850, lon: 78.4867, type: "THUNDERSTORM", text: "Thunderstorm warning: Loud thunder and light rain near Hussain Sagar." },
  { city: "Ahmedabad", state: "Gujarat", lat: 23.0225, lon: 72.5714, type: "HEATWAVE", text: "Mercury climbing past 44°C on SG Highway, severe dry heat." },
  { city: "Bhubaneswar", state: "Odisha", lat: 20.2961, lon: 85.8245, type: "STRONG_WIND", text: "High gusts shaking street lamps along Janpath road." },
  { city: "Patna", state: "Bihar", lat: 25.5941, lon: 85.1376, type: "FLOODING", text: "Water stagnation reported near Gandhi Maidan after heavy rainfall." }
];

let simIndex = 0;
setInterval(() => {
  if (wss.clients.size > 0) {
    const loc = SIMULATED_CITIES[simIndex % SIMULATED_CITIES.length];
    simIndex++;
    const newSimEvent = {
      id: `evt-live-${Date.now().toString().slice(-4)}`,
      source: "SOCIAL_SIMULATED",
      rawText: loc.text,
      mediaUrls: [],
      reportedAt: new Date().toISOString(),
      ingestedAt: new Date().toISOString(),
      lat: loc.lat + (Math.random() - 0.5) * 0.05,
      lon: loc.lon + (Math.random() - 0.5) * 0.05,
      city: loc.city,
      state: loc.state,
      eventType: loc.type,
      classificationConfidence: 0.88,
      verificationStatus: "PENDING",
      trustScore: 48,
      factorBreakdown: { sourceTrust: 40, corroborationBoost: 0, crossMatchOfficial: 0, imageCheck: 0 },
      corroborationCount: 0,
      duplicateOfId: null,
      sourceMeta: { simulated: true }
    };
    events.unshift(newSimEvent);
    broadcast(newSimEvent);
  }
}, 12000); // Emits every 12 seconds when clients connected

server.listen(PORT, () => {
  console.log(`[Mock Server] Running on http://localhost:${PORT}`);
  console.log(`[Mock Server] WebSocket ready at ws://localhost:${PORT}/ws/live`);
});

const express = require('express');
const cors = require('cors');

const port = process.env.PORT || 3000;
const app = express();

app.use(cors());
app.use(express.json());

// Canonical feature descriptors for downstream wiring
const features = [
  { key: 'tuning', title: 'Precision Tuning Studio', message: 'Detailed tuning endpoints are coming soon.' },
  { key: 'reels', title: 'Car Reels', message: 'Video reels APIs are coming soon.' },
  { key: 'chat', title: 'Chat Paddock', message: 'Realtime chat channels are coming soon.' },
  { key: 'profile', title: 'Profile Controls', message: 'Account settings and preferences APIs are coming soon.' },
];

const comingSoonPayload = (featureKey) => {
  const feature = features.find((f) => f.key === featureKey);
  return {
    feature: feature?.key ?? featureKey,
    title: feature?.title ?? 'Coming Soon',
    status: 'coming_soon',
    message: feature?.message ?? 'This endpoint will be available soon.',
  };
};

app.get('/health', (_req, res) => {
  res.json({ ok: true, service: 'carilla-backend', uptime: process.uptime() });
});

app.get('/api/status', (_req, res) => {
  res.json({
    service: 'carilla-backend',
    status: 'ok',
    features: features.map((f) => ({
      key: f.key,
      title: f.title,
      status: 'coming_soon',
      message: f.message,
    })),
  });
});

app.get('/api/tuning', (_req, res) => res.json(comingSoonPayload('tuning')));
app.get('/api/reels', (_req, res) => res.json(comingSoonPayload('reels')));
app.get('/api/chat', (_req, res) => res.json(comingSoonPayload('chat')));
app.get('/api/profile', (_req, res) => res.json(comingSoonPayload('profile')));

app.use((_req, res) => {
  res.status(404).json({ error: 'not_found', message: 'Route not registered yet.' });
});

app.listen(port, () => {
  console.log(`Carilla backend listening on :${port}`);
});

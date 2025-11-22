const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const multer = require('multer');

const port = process.env.PORT || 3000;
const app = express();

app.use(cors());
app.use(express.json());

const features = [
  { key: 'tuning', title: 'Precision Tuning Studio', message: 'Detailed tuning endpoints are coming soon.' },
  { key: 'reels', title: 'Car Reels', message: 'Video reels APIs are coming soon.' },
  { key: 'chat', title: 'Chat Paddock', message: 'Realtime chat channels are coming soon.' },
  { key: 'profile', title: 'Profile Controls', message: 'Account settings and preferences APIs are coming soon.' },
];

function comingSoonPayload(featureKey) {
  const feature = features.find((item) => item.key === featureKey);
  if (feature) {
    return { key: feature.key, title: feature.title, message: feature.message };
  }
  return { key: featureKey, title: 'Unknown feature', message: 'No descriptor registered for this feature yet.' };
}

const uploadsRoot = path.join(__dirname, '..', 'uploads');
const userCarsDir = path.join(uploadsRoot, 'user_cars');
const tunedResultsDir = path.join(uploadsRoot, 'tuned_results');
const dataDir = path.join(__dirname, '..', 'data');
const tuningLogPath = path.join(dataDir, 'tuning_log.json');

[uploadsRoot, userCarsDir, tunedResultsDir, dataDir].forEach((dirPath) => {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
});

function appendTuningLog(entry) {
  try {
    let log = [];

    if (fs.existsSync(tuningLogPath)) {
      try {
        const raw = fs.readFileSync(tuningLogPath, 'utf8');
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          log = parsed;
        }
      } catch (err) {
        console.error('Failed to parse tuning log:', err);
      }
    }

    log.push(entry);
    fs.writeFileSync(tuningLogPath, JSON.stringify(log, null, 2));
  } catch (err) {
    console.error('Failed to append tuning log:', err);
  }
}

const allowedMimeTypes = ['image/jpeg', 'image/png', 'image/webp'];

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, userCarsDir),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname) || '';
    const suffix = ext.toLowerCase();
    const timestamp = Date.now();
    cb(null, `car_${timestamp}${suffix}`);
  },
});

function fileFilter(_req, file, cb) {
  if (allowedMimeTypes.includes(file.mimetype)) {
    cb(null, true);
  } else {
    cb(new Error('Unsupported file type'));
  }
}

const upload = multer({ storage, fileFilter });

app.get('/api/tuning', (_req, res) => res.json(comingSoonPayload('tuning')));
app.get('/api/reels', (_req, res) => res.json(comingSoonPayload('reels')));
app.get('/api/chat', (_req, res) => res.json(comingSoonPayload('chat')));
app.get('/api/profile', (_req, res) => res.json(comingSoonPayload('profile')));

app.post('/api/tuning/upload', upload.single('photo'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'missing_file', message: 'No photo uploaded.' });
  }

  const entry = {
    id: Date.now().toString(),
    created_at: new Date().toISOString(),
    original_path: req.file.path,
    tuned_path: null,
    status: 'uploaded',
  };

  appendTuningLog(entry);

  return res.status(200).json({
    success: true,
    message: 'Photo received. AI tuning is not wired yet, but storage is ready.',
    job: entry,
  });
});

app.get('/api/tuning/log', (_req, res) => {
  try {
    if (!fs.existsSync(tuningLogPath)) {
      return res.json([]);
    }

    const raw = fs.readFileSync(tuningLogPath, 'utf8');
    const parsed = JSON.parse(raw);

    if (!Array.isArray(parsed)) {
      return res.json([]);
    }

    return res.json(parsed);
  } catch (err) {
    console.error('Failed to read tuning log:', err);
    return res.status(500).json({ error: 'log_read_failed' });
  }
});

app.use((_req, res) => {
  res.status(404).json({ error: 'not_found', message: 'Route not registered yet.' });
});

app.listen(port, () => {
  console.log(`Carilla backend listening on :${port}`);
});

const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Percorsi per i dati
const dataDir = path.join(__dirname, 'data');
const footballFile = path.join(dataDir, 'football.json');
const techFile = path.join(dataDir, 'tech.json');
const statsFile = path.join(dataDir, 'stats.json');

// Assicurati che i file di dati esistano
function ensureDataFiles() {
  if (!fs.existsSync(footballFile)) {
    fs.writeFileSync(footballFile, JSON.stringify([], null, 2));
  }
  if (!fs.existsSync(techFile)) {
    fs.writeFileSync(techFile, JSON.stringify([], null, 2));
  }
  if (!fs.existsSync(statsFile)) {
    fs.writeFileSync(statsFile, JSON.stringify({
      tasksCompleted: 0,
      lastUpdate: new Date().toLocaleTimeString('it-IT'),
      agentsStatus: {}
    }, null, 2));
  }
}

// Leggi i dati
function readData(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (err) {
    console.error(`Errore lettura ${filePath}:`, err.message);
    return [];
  }
}

// Scrivi i dati
function writeData(filePath, data) {
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
  } catch (err) {
    console.error(`Errore scrittura ${filePath}:`, err.message);
  }
}

// API Endpoints

// GET /api/content - Ottieni tutti i contenuti
app.get('/api/content', (req, res) => {
  ensureDataFiles();
  const football = readData(footballFile);
  const tech = readData(techFile);
  const stats = readData(statsFile);

  res.json({
    football: football.slice(0, 10),
    tech: tech.slice(0, 10),
    stats: stats
  });
});

// POST /api/football - Aggiungi articolo calcio
app.post('/api/football', (req, res) => {
  const { title, description, category, date } = req.body;
  const football = readData(footballFile);

  const article = {
    id: Date.now(),
    title,
    description,
    category,
    date: date || new Date().toLocaleDateString('it-IT'),
    createdAt: new Date().toISOString()
  };

  football.unshift(article);
  football.splice(100); // Mantieni solo i 100 più recenti
  writeData(footballFile, football);

  res.json({ success: true, article });
});

// POST /api/tech - Aggiungi articolo tech
app.post('/api/tech', (req, res) => {
  const { title, description, category, date } = req.body;
  const tech = readData(techFile);

  const article = {
    id: Date.now(),
    title,
    description,
    category,
    date: date || new Date().toLocaleDateString('it-IT'),
    createdAt: new Date().toISOString()
  };

  tech.unshift(article);
  tech.splice(100);
  writeData(techFile, tech);

  res.json({ success: true, article });
});

// POST /api/stats - Aggiorna statistiche
app.post('/api/stats', (req, res) => {
  const { tasksCompleted, agentStatus } = req.body;
  const stats = readData(statsFile);

  if (tasksCompleted !== undefined) {
    stats.tasksCompleted = tasksCompleted;
  }

  if (agentStatus) {
    stats.agentsStatus = { ...stats.agentsStatus, ...agentStatus };
  }

  stats.lastUpdate = new Date().toLocaleTimeString('it-IT');
  writeData(statsFile, stats);

  res.json({ success: true, stats });
});

// GET /api/stats - Ottieni statistiche
app.get('/api/stats', (req, res) => {
  ensureDataFiles();
  const stats = readData(statsFile);
  res.json(stats);
});

// DELETE /api/content - Cancella tutti i contenuti (utility)
app.delete('/api/content', (req, res) => {
  writeData(footballFile, []);
  writeData(techFile, []);
  res.json({ success: true, message: 'Contenuti eliminati' });
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not Found' });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Server Error:', err);
  res.status(500).json({ error: 'Internal Server Error' });
});

// Avvia il server
app.listen(PORT, () => {
  console.log(`🚀 Server avviato su http://localhost:${PORT}`);
  console.log(`📱 Landing page disponibile: http://localhost:${PORT}`);
  console.log(`🔌 API disponibile: http://localhost:${PORT}/api`);
  ensureDataFiles();
});

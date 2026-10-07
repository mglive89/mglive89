# 🚀 Calcio Agents - Configurazione

## Descrizione del Progetto

Landing page dinamica che si aggiorna automaticamente con notizie di calcio italiano, Champions League e ultime notizie di tecnologia/AI.

Il sistema è gestito da **5 agenti autonomi** che lavorano continuamente per mantenerla viva e interessante.

## 🤖 I 5 Agenti

### 1. **Football Agent** ⚽
- **Ruolo**: Raccoglie notizie di calcio
- **Frequenza**: Ogni 60 secondi
- **Compiti**:
  - Scraping notizie Serie A e Champions League
  - Aggiornamento live dei risultati
  - Notizie di calciomercato
  - Analisi delle partite

**File**: `agents/football-agent.js`

### 2. **Tech/AI Agent** 🤖
- **Ruolo**: Trova ultime notizie di tecnologia e AI
- **Frequenza**: Ogni 90 secondi
- **Compiti**:
  - Monitoraggio breakthroughs di AI
  - Notizie da ArXiv, HackerNews, Medium
  - Aggiornamenti su LLMs e modelli di IA
  - Trend tecnologici globali

**File**: `agents/tech-agent.js`

### 3. **Designer Agent** 🎨
- **Ruolo**: Mantiene la pagina bella e moderna
- **Frequenza**: Ogni 120 secondi
- **Compiti**:
  - Ottimizzazione design e UI
  - Miglioramento UX
  - Accessibilità e performance
  - Responsiveness mobile

**File**: `agents/designer-agent.js`

### 4. **QA/Bug Agent** 🐛
- **Ruolo**: Controlla errori e bug
- **Frequenza**: Ogni 45 secondi
- **Compiti**:
  - Test suite automatici
  - Verifica health check API
  - Monitoraggio performance
  - Security scanning

**File**: `agents/qa-agent.js`

### 5. **Orchestrator** ⚙️
- **Ruolo**: Coordina tutti gli altri agenti
- **Frequenza**: Continua (ogni 1 secondo)
- **Compiti**:
  - Gestione timing esecuzione agenti
  - Statistica e reporting
  - Health monitoring
  - Coordinamento workflow

**File**: `agents/orchestrator.js`

## 📁 Struttura del Progetto

```
mglive89/
├── public/
│   └── index.html          # Landing page (HTML/CSS/JS)
├── agents/
│   ├── football-agent.js   # Agente calcio
│   ├── tech-agent.js       # Agente tech/AI
│   ├── designer-agent.js   # Agente designer
│   ├── qa-agent.js         # Agente QA
│   └── orchestrator.js     # Orchestratore
├── data/
│   ├── football.json       # Articoli calcio
│   ├── tech.json          # Articoli tech
│   └── stats.json         # Statistiche sistema
├── logs/
│   ├── design.log         # Log designer
│   └── qa.log             # Log QA
├── server.js              # Server Express
├── package.json           # Dipendenze
└── CONFIG.md              # Questo file
```

## 🚀 Installazione e Avvio

### 1. Installa dipendenze
```bash
cd mglive89
npm install
```

### 2. Avvia il server principale
```bash
npm start
```

Il server parte su `http://localhost:3000`

### 3. In un'altro terminale, avvia gli agenti
```bash
npm run agents
```

## 🌐 Accesso

- **Landing Page**: http://localhost:3000
- **API Base**: http://localhost:3000/api
- **Health Check**: http://localhost:3000/api/health

## 📡 API Endpoints

### GET /api/content
Ottieni tutti i contenuti (calcio + tech)

```bash
curl http://localhost:3000/api/content
```

Risposta:
```json
{
  "football": [...],
  "tech": [...],
  "stats": {...}
}
```

### POST /api/football
Aggiungi articolo calcio

```bash
curl -X POST http://localhost:3000/api/football \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Inter vince il derby",
    "description": "Grande partita...",
    "category": "Serie A"
  }'
```

### POST /api/tech
Aggiungi articolo tech

```bash
curl -X POST http://localhost:3000/api/tech \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Claude AI breaks record",
    "description": "Nuovo benchmark...",
    "category": "AI"
  }'
```

### POST /api/stats
Aggiorna statistiche

```bash
curl -X POST http://localhost:3000/api/stats \
  -H "Content-Type: application/json" \
  -d '{
    "tasksCompleted": 42,
    "agentStatus": {
      "Football Agent": "running"
    }
  }'
```

### GET /api/stats
Ottieni statistiche

```bash
curl http://localhost:3000/api/stats
```

## 🔄 Come Funziona il Flusso

```
┌─────────────────────────────────────────────────────┐
│           ORCHESTRATOR (Ogni 1 secondo)             │
└────────┬────────────────────────────────────────────┘
         │
         ├─→ Football Agent (Ogni 60s)
         │   └─→ Scrape news → POST /api/football
         │
         ├─→ Tech Agent (Ogni 90s)
         │   └─→ Find articles → POST /api/tech
         │
         ├─→ Designer Agent (Ogni 120s)
         │   └─→ Optimize UI → Log improvements
         │
         ├─→ QA Agent (Ogni 45s)
         │   └─→ Run tests → Report issues
         │
         └─→ Update Stats (Continuo)
             └─→ POST /api/stats
```

## 📊 Monitoraggio

### Console Output
L'orchestrator stampa in console:
- Stato di ogni agente
- Ultimo run time
- Task completati
- Errori riscontrati

### File Log
- `logs/design.log` - Attività del designer
- `logs/qa.log` - Bug e problemi trovati

### Dashboard
La landing page mostra in tempo reale:
- Badge agenti attivi
- Numero articoli per categoria
- Timestamp ultimo aggiornamento
- Health check del sistema

## ⚙️ Configurazione Personalizzata

### Modificare intervalli agenti
In `agents/orchestrator.js`:

```javascript
this.agents = [
  { agent: new FootballAgent(), interval: 60000, lastRun: 0 }, // 60 secondi
  { agent: new TechAgent(), interval: 90000, lastRun: 0 },      // 90 secondi
  // ...
];
```

### Aggiungere nuove categorie di notizie
1. Crea nuovo file agente: `agents/newcategory-agent.js`
2. Aggiungi alla lista agenti in `orchestrator.js`
3. Crea nuovo endpoint in `server.js`

### Personalizzare tema UI
Modifica le variabili CSS in `public/index.html`:

```css
:root {
  --primary: #1e3a8a;
  --secondary: #dc2626;
  --accent: #0ea5e9;
  --dark: #0f172a;
  --light: #f1f5f9;
  --success: #16a34a;
}
```

## 🔐 Sicurezza

- CORS abilitato (configurabile)
- Validazione input API
- Rate limiting consigliato per produzione
- HTTPS raccomandato per deployment

## 📈 Performance

- Landing page: ~200ms load time
- API response: <100ms
- Database queries: Cached in memory (JSON files)
- Agenti: Esecuzione non-blocking

## 🚨 Troubleshooting

### "Cannot find module 'express'"
```bash
npm install
```

### Server non parte sulla porta 3000
```bash
PORT=8000 npm start
```

### Agenti non aggiornano la pagina
- Verifica che server e agenti siano in esecuzione
- Controlla console per errori
- Verifica logs in `logs/`

## 📝 Sviluppo Futuro

- [ ] Integrazione API reali (football-data.org, NewsAPI)
- [ ] Database persistente (MongoDB/PostgreSQL)
- [ ] Sistema di cache con Redis
- [ ] WebSocket per aggiornamenti real-time
- [ ] Notification system (Email/Telegram)
- [ ] Machine Learning per ranking articoli
- [ ] User personalization
- [ ] Dark mode toggle lato client

## 📄 Licenza

MIT

## 👨‍💻 Autore

Marco Gallo - marcogallo22@gmail.com

# ⚡ Quick Start - Calcio Agents

## 🎯 Obiettivo
Landing page che si aggiorna automaticamente con notizie di calcio e AI, gestita da 5 agenti autonomi intelligenti.

## ⚡ Avvio Rapido (2 minuti)

### Opzione 1: Modalità Produzione

```bash
# 1. Installa dipendenze
npm install

# 2. In terminale 1: Avvia il server
npm start

# 3. In terminale 2: Avvia gli agenti
npm run agents

# 4. Apri il browser
# http://localhost:3000
```

### Opzione 2: Modalità Sviluppo

```bash
# Con node-mon per auto-reload
npm install -D nodemon

# Package.json
{
  "scripts": {
    "dev": "nodemon server.js",
    "dev:agents": "nodemon agents/orchestrator.js"
  }
}

# Terminale 1
npm run dev

# Terminale 2
npm run dev:agents
```

## 📺 Cosa Vedrai

### Landing Page
- Header con badge di agenti attivi
- Sezione "Notizie Calcio" con articoli live
- Sezione "Notizie Tech/AI" con ultimi sviluppi
- Sidebar con status degli agenti
- Sistema di aggiornamento automatico

### Console (Orchestrator)
```
============================================================
🚀 CALCIO AGENTS ORCHESTRATOR AVVIATO
============================================================
📱 Landing Page: http://localhost:3000
🔌 API: http://localhost:3000/api
📊 Agenti: 4 in esecuzione
============================================================

📊 [15:23:45] STATUS SISTEMA
────────────────────────────────────────────────────────────
⏱️  Uptime: 2m 15s
✅ Task Completati: 8
📝 Errori: 0
────────────────────────────────────────────────────────────
✅ Football Agent       | Ultimo: 15:23:30
✅ Tech/AI Agent        | Ultimo: 15:22:15
✅ Designer Agent       | Ultimo: 15:23:00
✅ QA/Bug Agent         | Ultimo: 15:23:10
────────────────────────────────────────────────────────────
```

## 🤖 Come Funzionano gli Agenti

### ⚽ Football Agent
- Raccoglie notizie di calcio italiano e Champions
- Cerca articoli da fonti esterne
- Pubblica nuovi contenuti ogni 60 secondi
- Simula il recupero da API reali

### 🤖 Tech/AI Agent
- Trova ultime notizie di tecnologia e AI
- Cerca articoli da TechCrunch, ArXiv, HackerNews
- Pubblica articoli ogni 90 secondi
- Suddivide in categorie (LLM, Infrastructure, etc.)

### 🎨 Designer Agent
- Monitora e migliora UI/UX continuamente
- Ottimizza accessibilità e performance
- Verifica responsiveness mobile
- Registra miglioramenti applicati

### 🐛 QA/Bug Agent
- Esegue test suite automatici ogni 45 secondi
- Verifica salute API e database
- Controlla performance e memory leaks
- Genera report di errori e bug

### ⚙️ Orchestrator
- Coordina tutti e 4 gli agenti
- Gestisce timing e priorità
- Raccoglie statistiche
- Mantiene salute complessiva del sistema

## 📊 Monitoraggio

### Dashboard Live
Visita http://localhost:3000 per vedere:
- ✅ Agenti in esecuzione
- 📈 Numero articoli per categoria
- 🔄 Timestamp ultimi aggiornamenti
- 💚 Health score del sistema

### API Status
```bash
curl http://localhost:3000/api/health
# {"status":"ok","timestamp":"2024-10-07T15:23:45Z","uptime":135}
```

### View Articoli
```bash
curl http://localhost:3000/api/content
# {football: [...], tech: [...], stats: {...}}
```

## 🛠️ Aggiungere Articoli Manualmente

```bash
# Articolo calcio
curl -X POST http://localhost:3000/api/football \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Inter domina il derby",
    "description": "Bella vittoria con tre gol",
    "category": "Serie A",
    "date": "Oggi"
  }'

# Articolo tech
curl -X POST http://localhost:3000/api/tech \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Claude AI record nuovo",
    "description": "Anthropic annuncia breakthrough",
    "category": "AI",
    "date": "Oggi"
  }'
```

## 📝 File Importanti

| File | Descrizione |
|------|-------------|
| `public/index.html` | Landing page (HTML/CSS/JS) |
| `server.js` | Server Express |
| `agents/orchestrator.js` | Orchestratore agenti |
| `agents/football-agent.js` | Agente calcio |
| `agents/tech-agent.js` | Agente tech/AI |
| `agents/designer-agent.js` | Agente designer |
| `agents/qa-agent.js` | Agente QA |
| `data/*.json` | Articoli e statistiche |
| `logs/*.log` | File log agenti |

## 🔌 Integrazioni API (Opzionali)

### Per usare API reali al posto della simulazione:

#### Football Data
```javascript
// football-agent.js
const footballApiKey = process.env.FOOTBALL_API_KEY;
const response = await fetch('https://api.football-data.org/v4/matches', {
  headers: { 'X-Auth-Token': footballApiKey }
});
```

#### NewsAPI
```javascript
// tech-agent.js
const newsApiKey = process.env.NEWS_API_KEY;
const response = await fetch(
  `https://newsapi.org/v2/everything?q=AI%20technology&apiKey=${newsApiKey}`
);
```

## 🚨 Risoluzione Problemi

### Errore: "Cannot find module 'express'"
```bash
npm install
```

### Errore: "EADDRINUSE: address already in use :::3000"
```bash
# Cambia porta
PORT=8000 npm start

# O uccidi il processo precedente
lsof -i :3000
kill -9 <PID>
```

### Agenti non aggiornano la pagina
1. Verifica che entrambi server e agenti siano in esecuzione
2. Controlla browser console per errori
3. Visualizza logs: `tail -f logs/*.log`
4. Verifica http://localhost:3000/api/health

### API non risponde
```bash
# Verifica server è in esecuzione
curl http://localhost:3000/api/health
# Se non risponde, riavvia: Ctrl+C e npm start
```

## 📚 Approfondimenti

- **Full Config**: Leggi `CONFIG.md` per documentazione completa
- **API Docs**: Tutte le endpoint sono documentate in `server.js`
- **Architecture**: Vedi diagramma flusso agenti in `CONFIG.md`

## 🎓 Cosa Imparare da Questo Progetto

1. **Autonomous Agents**: Come creare agenti che lavorano in modo indipendente
2. **Orchestration**: Coordinarli centralmente con un orchestratore
3. **API Design**: REST API con Express.js
4. **Frontend Modern**: HTML/CSS/JS moderno e responsivo
5. **Real-time Updates**: Pagina che si aggiorna senza refresh
6. **Monitoring**: Sistema di health check e reporting

## 🚀 Prossimi Step

1. ✅ Integra API reali per notizie
2. ✅ Aggiungi database persistente (MongoDB)
3. ✅ Deploy su server (AWS/Heroku)
4. ✅ Aggiungi WebSocket per aggiornamenti real-time
5. ✅ Sistema di notifiche (Email/Telegram)
6. ✅ Machine Learning per ranking

## 💬 Supporto

Per domande o problemi, controlla:
- `CONFIG.md` - Documentazione completa
- `server.js` - API dettagliate
- `agents/*.js` - Logica agenti
- Console output - Diagnostica

---

**Goditi il tuo sistema di agenti autonomi! 🚀**

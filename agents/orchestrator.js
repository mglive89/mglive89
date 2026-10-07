/**
 * Orchestrator Agent - Coordina tutti gli altri agenti autonomi
 * Gestisce l'esecuzione, il timing e la salute complessiva del sistema
 */

const FootballAgent = require('./football-agent');
const TechAgent = require('./tech-agent');
const DesignerAgent = require('./designer-agent');
const QAAgent = require('./qa-agent');

class Orchestrator {
  constructor() {
    this.name = '⚙️ Orchestrator';
    this.agents = [
      { agent: new FootballAgent(), interval: 60000, lastRun: 0 },
      { agent: new TechAgent(), interval: 90000, lastRun: 0 },
      { agent: new DesignerAgent(), interval: 120000, lastRun: 0 },
      { agent: new QAAgent(), interval: 45000, lastRun: 0 }
    ];
    this.stats = {
      tasksCompleted: 0,
      agentsStatus: {},
      startTime: new Date(),
      errors: []
    };
    this.running = false;
  }

  start() {
    console.log('\n' + '='.repeat(60));
    console.log('🚀 CALCIO AGENTS ORCHESTRATOR AVVIATO');
    console.log('='.repeat(60));
    console.log(`📱 Landing Page: http://localhost:3000`);
    console.log(`🔌 API: http://localhost:3000/api`);
    console.log(`📊 Agenti: ${this.agents.length} in esecuzione`);
    console.log('='.repeat(60) + '\n');

    this.running = true;

    // Esegui immediatamente la prima volta
    this.executeAgents();

    // Poi ogni secondo controlla se qualche agente deve girare
    this.mainLoop = setInterval(() => {
      this.executeAgents();
    }, 1000);

    // Aggiorna statistiche ogni 5 secondi
    this.statsInterval = setInterval(() => {
      this.updateStats();
    }, 5000);
  }

  async executeAgents() {
    const now = Date.now();

    for (const agentWrapper of this.agents) {
      const timeSinceLastRun = now - agentWrapper.lastRun;

      // Se è passato abbastanza tempo, esegui l'agente
      if (timeSinceLastRun >= agentWrapper.interval) {
        agentWrapper.lastRun = now;

        try {
          const result = await agentWrapper.agent.run();

          this.stats.agentsStatus[agentWrapper.agent.name] = {
            status: result.success ? 'running' : 'error',
            lastRun: new Date().toISOString(),
            result: result
          };

          if (result.success) {
            this.stats.tasksCompleted++;
          } else {
            this.stats.errors.push({
              agent: agentWrapper.agent.name,
              error: result.error,
              timestamp: new Date().toISOString()
            });
          }

          // Aggiorna statistiche sul server
          await this.updateServerStats();
        } catch (error) {
          console.error(`Errore nel lanciare agente: ${error.message}`);
          this.stats.errors.push({
            agent: agentWrapper.agent.name,
            error: error.message,
            timestamp: new Date().toISOString()
          });
        }
      }
    }
  }

  async updateServerStats() {
    try {
      const stats = {
        tasksCompleted: this.stats.tasksCompleted,
        agentStatus: this.stats.agentsStatus
      };

      await fetch('http://localhost:3000/api/stats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(stats)
      });
    } catch (error) {
      // Server offline, continua comunque
    }
  }

  updateStats() {
    const uptime = Math.floor((Date.now() - this.stats.startTime) / 1000);
    const uptimeFormatted = `${Math.floor(uptime / 60)}m ${uptime % 60}s`;

    console.log(`\n📊 [${new Date().toLocaleTimeString('it-IT')}] STATUS SISTEMA`);
    console.log('─'.repeat(60));
    console.log(`⏱️  Uptime: ${uptimeFormatted}`);
    console.log(`✅ Task Completati: ${this.stats.tasksCompleted}`);
    console.log(`📝 Errori: ${this.stats.errors.length}`);
    console.log('─'.repeat(60));

    // Mostra stato di ogni agente
    this.agents.forEach(agentWrapper => {
      const status = this.stats.agentsStatus[agentWrapper.agent.name];
      const statusIcon = status && status.status === 'running' ? '✅' : '⏳';
      const lastRun = status ? new Date(status.lastRun).toLocaleTimeString('it-IT') : 'Never';
      console.log(`${statusIcon} ${agentWrapper.agent.name.padEnd(20)} | Ultimo: ${lastRun}`);
    });
    console.log('─'.repeat(60) + '\n');
  }

  stop() {
    console.log('\n⛔ Orchestrator fermato');
    this.running = false;
    clearInterval(this.mainLoop);
    clearInterval(this.statsInterval);
  }

  getStats() {
    return this.stats;
  }
}

// Avvia l'orchestrator
const orchestrator = new Orchestrator();

// Gestisci segnali di termination
process.on('SIGINT', () => {
  console.log('\n\n🛑 Ricevuto SIGINT, arresto graceful...');
  orchestrator.stop();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n\n🛑 Ricevuto SIGTERM, arresto graceful...');
  orchestrator.stop();
  process.exit(0);
});

// Avvia
orchestrator.start();

module.exports = Orchestrator;

const fs = require('fs');
const path = require('path');

/**
 * Football Agent - Raccoglie notizie di calcio italiano e Champions League
 * Simula il recupero di notizie da varie fonti
 */

class FootballAgent {
  constructor() {
    this.name = 'Football Agent';
    this.interval = 60000; // Ogni 60 secondi
    this.newsDatabase = [
      {
        title: "Inter-Milan, il derby dei due mondi",
        description: "La rivalità milanese infiamma San Siro. Momenti di tensione tra i difensori durante il warming-up",
        category: "Serie A"
      },
      {
        title: "Napoli continua la rincorsa scudetto",
        description: "Gli azzurri rimangono in scia dei leader con una prestazione convincente. Osimhen decisivo in attacco.",
        category: "Serie A"
      },
      {
        title: "Juventus, rinnovo per il top player",
        description: "La Juve blinds il suo campione con un contratto pluriennale ricco di bonus e incentivi",
        category: "Calciomercato"
      },
      {
        title: "Manchester City elimina il Bayern",
        description: "Pep Guardiola torna in Champions con una prestazione tattica superiore ai tedeschi",
        category: "Champions League"
      },
      {
        title: "Real Madrid, Benzema segna un'altra doppietta",
        description: "Karim continua a dominare in Europa. Il Real Madrid mostra muscoli nei quarti di Champions",
        category: "Champions League"
      },
      {
        title: "PSG punta al tridente d'oro",
        description: "Il calciomercato francese si infiamma con l'arrivo della nuova stella brasiliana",
        category: "Calciomercato"
      },
      {
        title: "Atalanta, la Dea fa festa",
        description: "La squadra di Gasperini continua il suo cammino sorprendente in Europa",
        category: "Serie A"
      },
      {
        title: "Liverpool, Klopp prepara la rimonta",
        description: "I Reds si preparano per un'altra stagione di fuoco con il mercato che si anima",
        category: "Premier League"
      }
    ];
  }

  async run() {
    console.log(`\n[${this.getTime()}] 🏃 ${this.name} in esecuzione...`);

    try {
      // Simula la raccolta di notizie da fonti esterne
      const newArticles = await this.fetchFootballNews();

      // Salva gli articoli
      await this.saveArticles(newArticles);

      console.log(`✅ ${this.name} completato: ${newArticles.length} articoli trovati`);
      return {
        success: true,
        articlesFound: newArticles.length,
        agent: this.name
      };
    } catch (error) {
      console.error(`❌ ${this.name} errore:`, error.message);
      return {
        success: false,
        error: error.message,
        agent: this.name
      };
    }
  }

  async fetchFootballNews() {
    // Simula il recupero di notizie da API esterne
    // In produzione, userebbero API come:
    // - football-data.org
    // - ESPN API
    // - Sky Sports API
    // - Opta Sports API

    // Seleziona articoli casuali dal database simulato
    const articles = [];
    const count = Math.floor(Math.random() * 3) + 1; // 1-3 articoli per esecuzione

    for (let i = 0; i < count; i++) {
      const randomIndex = Math.floor(Math.random() * this.newsDatabase.length);
      const baseNews = this.newsDatabase[randomIndex];

      articles.push({
        title: `${baseNews.title} [${new Date().toLocaleTimeString()}]`,
        description: baseNews.description,
        category: baseNews.category,
        date: this.formatDate(new Date()),
        source: this.getRandomSource(),
        credibility: Math.floor(Math.random() * 40) + 60 // 60-100%
      });
    }

    return articles;
  }

  async saveArticles(articles) {
    const apiUrl = 'http://localhost:3000/api/football';

    for (const article of articles) {
      try {
        // Invia ogni articolo al server
        await fetch(apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(article)
        });
      } catch (error) {
        console.log(`   ⚠️  Impossibile inviare articolo al server (forse offline): ${article.title}`);
      }
    }
  }

  getRandomSource() {
    const sources = ['Sky Sports', 'Goal.com', 'ESPN', 'Gazzetta dello Sport', 'Corriere dello Sport'];
    return sources[Math.floor(Math.random() * sources.length)];
  }

  formatDate(date) {
    const options = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return date.toLocaleDateString('it-IT', options);
  }

  getTime() {
    return new Date().toLocaleTimeString('it-IT');
  }
}

// Esporta per uso nel orchestrator
module.exports = FootballAgent;

// Se eseguito direttamente
if (require.main === module) {
  const agent = new FootballAgent();
  agent.run().then(result => {
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  });
}

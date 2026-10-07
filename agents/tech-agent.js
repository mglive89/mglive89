/**
 * Tech Agent - Raccoglie notizie di Tecnologia e Intelligenza Artificiale
 * Monitora gli ultimi sviluppi nel mondo della AI
 */

class TechAgent {
  constructor() {
    this.name = 'Tech/AI Agent';
    this.interval = 90000; // Ogni 90 secondi
    this.techDatabase = [
      {
        title: "Claude AI ridefinisce il futuro del reasoning",
        description: "Anthropic annuncia un nuovo breakthrough nel ragionamento logico. Latenza ridotta del 50% su problemi complessi.",
        category: "AI Reasoning"
      },
      {
        title: "OpenAI rilascia GPT-5 con multimodalità avanzata",
        description: "Il nuovo modello elabora simultaneamente testo, immagini, video e audio con accuratezza superiore.",
        category: "Large Language Models"
      },
      {
        title: "Google Gemini batte i benchmark di intelligenza",
        description: "Nuove metriche mostrano che Gemini Ultra supera tutti i competitor nel ragionamento matematico.",
        category: "AI Benchmarks"
      },
      {
        title: "Meta investisce miliardi in AI infrastrutture",
        description: "Meta annuncia il più grande data center per AI. Oltre 600,000 GPU H100 installate.",
        category: "AI Infrastructure"
      },
      {
        title: "DeepMind: AlphaFold risolve strutture proteiche",
        description: "L'AI di DeepMind scopre 2 milioni di nuove strutture proteiche in pochi giorni.",
        category: "Scientific AI"
      },
      {
        title: "Mistral AI lancia competitore a GPT-4",
        description: "Lo startup francese rilascia un modello open-source che rivaleggia con i top player globali.",
        category: "Open Source AI"
      },
      {
        title: "Microsoft integra Copilot in Windows 12",
        description: "L'assistente IA di Microsoft diventa centrale nel nuovo sistema operativo con accesso nativo.",
        category: "Consumer AI"
      },
      {
        title: "Apple sviluppa AI on-device per iPhone",
        description: "Privacy-first AI processing direttamente sul dispositivo senza cloud. Rivoluzione per i consumer.",
        category: "Mobile AI"
      },
      {
        title: "Nvidia annuncia GPU con 1 trilione di parametri",
        description: "La nuova architettura Blackwell supporta modelli esageratamente grandi con efficienza energetica.",
        category: "Hardware AI"
      },
      {
        title: "EU regula l'AI Act: impatti globali",
        description: "Le normative europee cominciano a influenzare lo sviluppo di IA in tutto il mondo.",
        category: "AI Regulation"
      }
    ];
  }

  async run() {
    console.log(`\n[${this.getTime()}] 🤖 ${this.name} in esecuzione...`);

    try {
      // Simula la raccolta di notizie tech
      const newArticles = await this.fetchTechNews();

      // Salva gli articoli
      await this.saveArticles(newArticles);

      console.log(`✅ ${this.name} completato: ${newArticles.length} articoli trovati`);
      return {
        success: true,
        articlesFound: newArticles.length,
        agent: this.name,
        categories: this.extractCategories(newArticles)
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

  async fetchTechNews() {
    // Simula il recupero di notizie da API come:
    // - NewsAPI
    // - TechCrunch API
    // - HackerNews API
    // - Medium API
    // - ArXiv API

    const articles = [];
    const count = Math.floor(Math.random() * 3) + 1; // 1-3 articoli

    for (let i = 0; i < count; i++) {
      const randomIndex = Math.floor(Math.random() * this.techDatabase.length);
      const baseNews = this.techDatabase[randomIndex];

      articles.push({
        title: `${baseNews.title} [${new Date().toLocaleTimeString()}]`,
        description: baseNews.description,
        category: baseNews.category,
        date: this.formatDate(new Date()),
        source: this.getRandomTechSource(),
        importance: Math.floor(Math.random() * 40) + 60, // 60-100%
        tags: this.generateTags(baseNews.category)
      });
    }

    return articles;
  }

  async saveArticles(articles) {
    const apiUrl = 'http://localhost:3000/api/tech';

    for (const article of articles) {
      try {
        await fetch(apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(article)
        });
      } catch (error) {
        console.log(`   ⚠️  Impossibile inviare articolo al server: ${article.title}`);
      }
    }
  }

  extractCategories(articles) {
    return [...new Set(articles.map(a => a.category))];
  }

  generateTags(category) {
    const tags = {
      'AI Reasoning': ['reasoning', 'logic', 'benchmarks'],
      'Large Language Models': ['llm', 'nlp', 'multimodal'],
      'AI Benchmarks': ['benchmarks', 'evaluation', 'performance'],
      'AI Infrastructure': ['gpu', 'data-center', 'cloud'],
      'Scientific AI': ['protein-folding', 'biology', 'discovery'],
      'Open Source AI': ['open-source', 'community', 'models'],
      'Consumer AI': ['mobile', 'desktop', 'privacy'],
      'Mobile AI': ['on-device', 'edge-ai', 'privacy'],
      'Hardware AI': ['gpu', 'chips', 'inference'],
      'AI Regulation': ['policy', 'governance', 'compliance']
    };
    return tags[category] || ['ai', 'technology'];
  }

  getRandomTechSource() {
    const sources = ['ArXiv', 'TechCrunch', 'HackerNews', 'The Verge', 'Medium', 'KDnuggets'];
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

module.exports = TechAgent;

if (require.main === module) {
  const agent = new TechAgent();
  agent.run().then(result => {
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  });
}

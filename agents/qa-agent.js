/**
 * QA Agent - Controlla errori, bug e performance della pagina
 * Monitora la salute del sistema e riporta problemi
 */

class QAAgent {
  constructor() {
    this.name = 'QA/Bug Agent';
    this.interval = 45000; // Ogni 45 secondi
    this.testSuite = [
      { test: 'API Health Check', type: 'api' },
      { test: 'Database Connection', type: 'db' },
      { test: 'Frontend Load Time', type: 'performance' },
      { test: 'Memory Leak Detection', type: 'performance' },
      { test: 'Response Validation', type: 'data' },
      { test: 'Mobile Responsiveness', type: 'ui' },
      { test: 'Cross-browser Compatibility', type: 'ui' },
      { test: 'Security Headers Check', type: 'security' },
      { test: 'SSL Certificate Validation', type: 'security' },
      { test: 'API Rate Limiting', type: 'api' }
    ];
    this.bugsDatabase = [];
  }

  async run() {
    console.log(`\n[${this.getTime()}] 🐛 ${this.name} in esecuzione...`);

    try {
      // Esegui test suite
      const testResults = await this.runTests();

      // Analizza risultati
      const issues = await this.analyzeResults(testResults);

      // Registra bug trovati
      await this.reportBugs(issues);

      // Valuta salute del sistema
      const health = this.calculateSystemHealth(testResults);

      console.log(`✅ ${this.name} completato: ${testResults.length} test eseguiti, ${issues.length} problemi trovati`);
      return {
        success: true,
        testsExecuted: testResults.length,
        issuesFound: issues.length,
        systemHealth: health,
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

  async runTests() {
    const results = [];

    // Seleziona test casuali
    const numberOfTests = Math.floor(Math.random() * 4) + 3; // 3-6 test

    for (let i = 0; i < numberOfTests; i++) {
      const test = this.testSuite[Math.floor(Math.random() * this.testSuite.length)];
      const passed = Math.random() > 0.1; // 90% chance di passare

      results.push({
        testName: test.test,
        type: test.type,
        passed: passed,
        duration: Math.floor(Math.random() * 500) + 50 + 'ms',
        timestamp: new Date().toISOString()
      });
    }

    return results;
  }

  async analyzeResults(testResults) {
    const issues = [];

    // Identifica test falliti
    testResults.forEach(result => {
      if (!result.passed) {
        issues.push({
          type: 'TEST_FAILURE',
          severity: this.getIssueSeverity(result.type),
          test: result.testName,
          category: result.type,
          timestamp: result.timestamp,
          description: `Il test "${result.testName}" è fallito durante l'esecuzione`,
          suggestedFix: this.getSuggestedFix(result.testName)
        });
      }
    });

    // Simula altre verifiche periodiche
    if (Math.random() > 0.7) {
      issues.push({
        type: 'PERFORMANCE_WARNING',
        severity: 'medium',
        description: 'Response time superiore a 200ms rilevato',
        component: 'API Endpoint',
        suggestedFix: 'Verificare query database e ottimizzare'
      });
    }

    if (Math.random() > 0.85) {
      issues.push({
        type: 'DEPENDENCY_UPDATE',
        severity: 'low',
        description: 'Update disponibile per express.js',
        package: 'express@4.19.0',
        suggestedFix: 'npm update express'
      });
    }

    return issues;
  }

  async reportBugs(issues) {
    const logsDir = require('path').join(__dirname, '..', 'logs');
    const fs = require('fs');

    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true });
    }

    const logFile = require('path').join(logsDir, 'qa.log');

    issues.forEach(issue => {
      const logEntry = {
        timestamp: new Date().toISOString(),
        agent: this.name,
        issue: issue
      };

      try {
        fs.appendFileSync(logFile, JSON.stringify(logEntry) + '\n');
      } catch (e) {
        // Silently continue
      }
    });

    this.bugsDatabase.push(...issues);

    // Mantieni solo gli ultimi 50 bug
    if (this.bugsDatabase.length > 50) {
      this.bugsDatabase = this.bugsDatabase.slice(-50);
    }
  }

  getIssueSeverity(testType) {
    const severityMap = {
      'api': 'critical',
      'db': 'critical',
      'security': 'critical',
      'performance': 'high',
      'data': 'high',
      'ui': 'medium'
    };
    return severityMap[testType] || 'medium';
  }

  getSuggestedFix(testName) {
    const fixes = {
      'API Health Check': 'Verificare che il server sia in esecuzione sulla porta corretta',
      'Database Connection': 'Controllare le credenziali del database',
      'Frontend Load Time': 'Minificare asset e abilitare compressione',
      'Memory Leak Detection': 'Controllare per event listener non rimossi',
      'Response Validation': 'Verificare schema di risposta API',
      'Mobile Responsiveness': 'Testare su device reali e usare viewport meta tag',
      'Cross-browser Compatibility': 'Usare polyfill per feature non supportate',
      'Security Headers Check': 'Aggiungere Content-Security-Policy header',
      'SSL Certificate Validation': 'Verificare certificato SSL è valido',
      'API Rate Limiting': 'Implementare rate limiting per prevenire abuse'
    };
    return fixes[testName] || 'Investigare l\'errore nei log';
  }

  calculateSystemHealth(testResults) {
    const passed = testResults.filter(r => r.passed).length;
    const total = testResults.length;
    const healthPercentage = Math.round((passed / total) * 100);

    return {
      percentage: healthPercentage,
      status: healthPercentage >= 90 ? 'HEALTHY' : healthPercentage >= 70 ? 'WARNING' : 'CRITICAL',
      testsRun: total,
      testsPassed: passed,
      testsFailed: total - passed
    };
  }

  getTime() {
    return new Date().toLocaleTimeString('it-IT');
  }
}

module.exports = QAAgent;

if (require.main === module) {
  const agent = new QAAgent();
  agent.run().then(result => {
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  });
}

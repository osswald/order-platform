<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1>Dashboard</h1>
      <p class="subtitle">Willkommen bei Vendiqo</p>
    </div>

    <div class="cards-grid">
      <div class="stat-card">
        <div class="card-icon">📋</div>
        <div class="card-content">
          <h3>Offene Bestellungen</h3>
          <p class="card-value">12</p>
          <p class="card-detail">In dieser Woche</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="card-icon">📦</div>
        <div class="card-content">
          <h3>Lagerbestand</h3>
          <p class="card-value">2,847</p>
          <p class="card-detail">Artikel im Lager</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="card-icon">💰</div>
        <div class="card-content">
          <h3>Umsatz (Monat)</h3>
          <p class="card-value">€45.2K</p>
          <p class="card-detail">+12% vs. Vormonat</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="card-icon">👥</div>
        <div class="card-content">
          <h3>Aktive Kunden</h3>
          <p class="card-value">156</p>
          <p class="card-detail">+8 diese Woche</p>
        </div>
      </div>
    </div>

    <div class="content-section">
      <div class="section-card">
        <h2>Kürzliche Aktivitäten</h2>
        <div class="activity-list">
          <div class="activity-item">
            <span class="activity-badge">✓</span>
            <div class="activity-text">
              <p class="activity-title">Bestellung #2451 erfolgreich abgeschlossen</p>
              <p class="activity-time">vor 2 Stunden</p>
            </div>
          </div>
          <div class="activity-item">
            <span class="activity-badge">→</span>
            <div class="activity-text">
              <p class="activity-title">Sendung #PRO-789 wurde versandt</p>
              <p class="activity-time">vor 4 Stunden</p>
            </div>
          </div>
          <div class="activity-item">
            <span class="activity-badge">⚠</span>
            <div class="activity-text">
              <p class="activity-title">Artikel "Widget Pro" Bestand niedrig</p>
              <p class="activity-time">vor 6 Stunden</p>
            </div>
          </div>
          <div class="activity-item">
            <span class="activity-badge">+</span>
            <div class="activity-text">
              <p class="activity-title">Neuer Kunde "TechCorp GmbH" hinzugefügt</p>
              <p class="activity-time">gestern</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Dashboard component - ready to integrate with real data
</script>

<style scoped>
.dashboard {
  padding: 2rem;
  background: var(--p-surface-ground);
  min-height: 100%;
}

.dashboard-header {
  margin-bottom: 2rem;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 2.2rem;
  color: var(--p-text-color);
  font-weight: 700;
}

.subtitle {
  margin: 0.5rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 1rem;
  font-weight: 500;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  display: flex;
  gap: 1.5rem;
  padding: 1.5rem;
  background: var(--p-surface-card);
  border: 1px solid var(--p-content-border-color);
  border-radius: 1rem;
  box-shadow: var(--p-card-shadow);
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  background: var(--p-primary-50);
  color: var(--p-primary-color);
  border-radius: 0.85rem;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.card-content {
  flex: 1;
}

.card-content h3 {
  margin: 0 0 0.5rem;
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.8;
}

.card-value {
  margin: 0.5rem 0 0.25rem;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.card-detail {
  margin: 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.content-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
}

.section-card {
  background: var(--p-surface-card);
  border: 1px solid var(--p-content-border-color);
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: var(--p-card-shadow);
}

.section-card h2 {
  margin: 0 0 1.5rem;
  color: var(--p-text-color);
  font-size: 1.2rem;
  font-weight: 700;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.activity-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: var(--p-surface-50);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  transition: all 0.3s ease;
}

.activity-item:hover {
  background: var(--p-surface-hover);
}

.activity-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  border-radius: 50%;
  font-size: 0.9rem;
  font-weight: 700;
  flex-shrink: 0;
}

.activity-text {
  flex: 1;
}

.activity-title {
  margin: 0;
  color: var(--p-text-color);
  font-weight: 600;
  font-size: 0.95rem;
}

.activity-time {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}

@media (max-width: 768px) {
  .dashboard {
    padding: 1rem;
  }

  .cards-grid {
    grid-template-columns: 1fr;
  }

  .content-section {
    grid-template-columns: 1fr;
  }

  .dashboard-header h1 {
    font-size: 1.8rem;
  }
}
</style>

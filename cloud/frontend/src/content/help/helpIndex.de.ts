export const helpCategories = [
  {
    id: 'getting-started',
    title: 'Erste Schritte',
    articles: [
      {
        slug: 'dashboard-overview',
        title: 'Dashboard',
        summary: 'Was die Übersicht anzeigt und wie Sie sie nutzen.',
        relatedRoutes: ['dashboard'],
      },
    ],
  },
  {
    id: 'events',
    title: 'Veranstaltungen',
    articles: [
      {
        slug: 'event-setup',
        title: 'Event einrichten',
        summary: 'Stammdaten, Stationen, Kellner, App-Layouts mit Farbpalette und weitere Konfiguration.',
        relatedRoutes: ['events', 'events-detail', 'events-new'],
      },
      {
        slug: 'waiters',
        title: 'Kellner verwalten',
        summary: 'Kellner anlegen, PINs vergeben und für Events vorbereiten.',
        relatedRoutes: ['waiters', 'waiters-detail', 'waiters-new'],
      },
      {
        slug: 'event-live-operations',
        title: 'Live-Betrieb',
        summary: 'Umsatz, Sammelrechnungen, Transaktionen und Kassensitzungen während laufender Events.',
        relatedRoutes: ['events-detail'],
      },
    ],
  },
  {
    id: 'catalog',
    title: 'Katalog',
    articles: [
      {
        slug: 'articles-and-categories',
        title: 'Artikel und Kategorien',
        summary: 'Artikel anlegen, Kategorien strukturieren und für Events bereitstellen.',
        relatedRoutes: ['articles', 'articles-detail', 'article-categories', 'article-categories-detail'],
      },
    ],
  },
  {
    id: 'appliances',
    title: 'Geräte',
    articles: [
      {
        slug: 'appliance-pairing',
        title: 'Raspberry Pi koppeln',
        summary: 'Server-Gerät anlegen und Pi mit Pairing-Code verbinden.',
        relatedRoutes: ['appliances', 'appliances-detail', 'appliances-new'],
      },
      {
        slug: 'appliance-lending',
        title: 'Geräteausleihen',
        summary: 'Aktive und geplante Ausleihen für Ihre Organisation einsehen.',
        relatedRoutes: ['appliance-lendings'],
      },
    ],
  },
  {
    id: 'payments',
    title: 'Zahlungen',
    articles: [
      {
        slug: 'stripe-connect',
        title: 'Stripe Connect',
        summary: 'Stripe-Konto verbinden und Kartenzahlung per Terminal aktivieren.',
        relatedRoutes: ['organisations', 'organisations-detail', 'stripe-connect-return', 'stripe-connect-refresh'],
      },
    ],
  },
  {
    id: 'administration',
    title: 'Verwaltung',
    articles: [
      {
        slug: 'roles-and-access',
        title: 'Rollen und Zugriff',
        summary: 'Plattform-Admin, Organisations-Admin und Mitglied — wer darf was?',
        relatedRoutes: ['hire-companies', 'hire-companies-detail', 'users', 'users-detail', 'no-access'],
      },
      {
        slug: 'organisation-setup',
        title: 'Organisation einrichten',
        summary: 'Stammdaten, Buchhaltung, Farbpalette, Geräteausleihen und Stripe für eine Organisation.',
        relatedRoutes: ['organisations', 'organisations-detail', 'organisations-new'],
      },
      {
        slug: 'tenant-settings',
        title: 'Verleiher-Einstellungen',
        summary: 'Verleiher-Stammdaten und Belegvorlagen auf Mandantenebene.',
        relatedRoutes: ['tenant-settings'],
      },
      {
        slug: 'user-management',
        title: 'Benutzer verwalten',
        summary: 'Benutzer anlegen, Rollen zuweisen und Organisationen verknüpfen.',
        relatedRoutes: ['users', 'users-detail', 'users-new'],
      },
    ],
  },
]

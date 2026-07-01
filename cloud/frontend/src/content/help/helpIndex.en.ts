export const helpCategories = [
  {
    id: 'getting-started',
    title: 'Getting started',
    articles: [
      {
        slug: 'dashboard-overview',
        title: 'Dashboard',
        summary: 'What the overview shows and how to use it.',
        relatedRoutes: ['dashboard'],
      },
    ],
  },
  {
    id: 'events',
    title: 'Events',
    articles: [
      {
        slug: 'event-setup',
        title: 'Set up an event',
        summary: 'Master data, stations, waiters, app layouts with color palette, and further configuration.',
        relatedRoutes: ['events', 'events-detail', 'events-new'],
      },
      {
        slug: 'waiters',
        title: 'Manage waiters',
        summary: 'Create waiters, assign PINs, and prepare them for events.',
        relatedRoutes: ['waiters', 'waiters-detail', 'waiters-new'],
      },
      {
        slug: 'event-live-operations',
        title: 'Live operations',
        summary: 'Sales, collective bills, transactions, and cash sessions during running events.',
        relatedRoutes: ['events-detail'],
      },
    ],
  },
  {
    id: 'catalog',
    title: 'Catalog',
    articles: [
      {
        slug: 'articles-and-categories',
        title: 'Articles and categories',
        summary: 'Create articles, structure categories, and prepare them for events.',
        relatedRoutes: ['articles', 'articles-detail', 'article-categories', 'article-categories-detail'],
      },
    ],
  },
  {
    id: 'appliances',
    title: 'Appliances',
    articles: [
      {
        slug: 'appliance-pairing',
        title: 'Pair a Raspberry Pi',
        summary: 'Create a server appliance and connect a Pi with a pairing code.',
        relatedRoutes: ['appliances', 'appliances-detail', 'appliances-new'],
      },
      {
        slug: 'appliance-lending',
        title: 'Appliance lending',
        summary: 'View active and planned lendings for your organisation.',
        relatedRoutes: ['appliance-lendings'],
      },
    ],
  },
  {
    id: 'payments',
    title: 'Payments',
    articles: [
      {
        slug: 'stripe-connect',
        title: 'Stripe Connect',
        summary: 'Connect a Stripe account and enable card payments via terminal.',
        relatedRoutes: ['organisations', 'organisations-detail', 'stripe-connect-return', 'stripe-connect-refresh'],
      },
    ],
  },
  {
    id: 'administration',
    title: 'Administration',
    articles: [
      {
        slug: 'roles-and-access',
        title: 'Roles and access',
        summary: 'Platform admin, organisation admin, and member — who can do what?',
        relatedRoutes: ['hire-companies', 'hire-companies-detail', 'users', 'users-detail', 'no-access'],
      },
      {
        slug: 'organisation-setup',
        title: 'Set up an organisation',
        summary: 'Master data, accounting, color palette, appliance lending, and Stripe for an organisation.',
        relatedRoutes: ['organisations', 'organisations-detail', 'organisations-new'],
      },
      {
        slug: 'tenant-settings',
        title: 'Tenant settings',
        summary: 'Hire-company profile and receipt templates at tenant level.',
        relatedRoutes: ['tenant-settings'],
      },
      {
        slug: 'user-management',
        title: 'Manage users',
        summary: 'Create users, assign roles, and link organisations.',
        relatedRoutes: ['users', 'users-detail', 'users-new'],
      },
    ],
  },
]

export function renderSiteHeader({ active = '' } = {}) {
  const navLink = (href, label, key) => {
    const isActive = active === key
    return `<a href="${href}"${isActive ? ' aria-current="page"' : ''}>${label}</a>`
  }

  return `
    <header class="site-header">
      <div class="site-header__inner">
        <a class="brand" href="/">
          <img class="brand__logo" src="/apple-touch-icon.png" alt="" width="40" height="40" />
          <span>Vendiqo</span>
        </a>
        <nav class="site-nav" aria-label="Hauptnavigation">
          ${navLink('https://admin.vendiqo.ch/', 'Admin', 'admin')}
          ${navLink('/datenschutz/', 'Datenschutz', 'datenschutz')}
        </nav>
      </div>
    </header>
  `
}

export function renderSiteFooter() {
  const year = new Date().getFullYear()
  return `
    <footer class="site-footer">
      <div class="site-footer__inner">
        <span>&copy; ${year} Vendiqo GmbH</span>
        <a href="/datenschutz/">Datenschutz</a>
      </div>
    </footer>
  `
}

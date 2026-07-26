export function renderSiteHeader({ active = '' } = {}) {
  const navLink = (href, label, key, { primary = false } = {}) => {
    const isActive = active === key
    const classes = [
      primary ? 'nav-link nav-link--primary' : 'nav-link',
      isActive ? 'is-active' : '',
    ]
      .filter(Boolean)
      .join(' ')
    return `<a class="${classes}" href="${href}"${isActive ? ' aria-current="page"' : ''}>${label}</a>`
  }

  return `
    <header class="site-header">
      <div class="site-header__inner">
        <a class="brand" href="/">
          <img class="brand__logo" src="/apple-touch-icon.png" alt="" width="40" height="40" />
          <span>Vendiqo</span>
        </a>
        <nav class="site-nav" aria-label="Hauptnavigation">
          ${navLink('/ablauf/', 'Ablauf', 'ablauf')}
          ${navLink('/funktionen/', 'Funktionen', 'funktionen')}
          ${navLink('/kontakt/', 'Mietanfrage', 'kontakt', { primary: true })}
          ${navLink('https://admin.vendiqo.ch/', 'Admin', 'admin')}
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

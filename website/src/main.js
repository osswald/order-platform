import './styles.css'
import { renderSiteFooter, renderSiteHeader } from './layout.js'

const headerMount = document.getElementById('site-header')
const footerMount = document.getElementById('site-footer')

if (headerMount) {
  headerMount.innerHTML = renderSiteHeader({ active: headerMount.dataset.active || '' })
}

if (footerMount) {
  footerMount.innerHTML = renderSiteFooter()
}

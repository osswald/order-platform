import MarkdownIt from 'markdown-it'
import datenschutzMarkdown from '../content/datenschutz.md?raw'
import './main.js'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })
const contentMount = document.getElementById('legal-content')

if (contentMount) {
  contentMount.innerHTML = md.render(datenschutzMarkdown)
}

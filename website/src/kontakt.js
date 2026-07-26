import './main.js'
import { API_BASE_URL } from './config.js'
import { validateInquiryFields } from './inquiryValidation.js'

const form = document.getElementById('rental-inquiry-form')
const statusEl = document.getElementById('form-status')
const submitBtn = document.getElementById('form-submit')

function setStatus(message, { error = false } = {}) {
  if (!statusEl) return
  statusEl.hidden = !message
  statusEl.textContent = message
  statusEl.classList.toggle('form-status--error', error)
  statusEl.classList.toggle('form-status--ok', Boolean(message) && !error)
}

if (form) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault()
    setStatus('')

    const formData = new FormData(form)
    const clientError = validateInquiryFields({
      name: formData.get('name'),
      organisation: formData.get('organisation'),
      email: formData.get('email'),
      timeframe: formData.get('timeframe'),
      message: formData.get('message'),
    })
    if (clientError) {
      setStatus(clientError, { error: true })
      return
    }

    const payload = {
      name: String(formData.get('name') || '').trim(),
      organisation: String(formData.get('organisation') || '').trim(),
      email: String(formData.get('email') || '').trim(),
      phone: String(formData.get('phone') || '').trim() || null,
      timeframe: String(formData.get('timeframe') || '').trim(),
      message: String(formData.get('message') || '').trim(),
      website: String(formData.get('website') || ''),
    }

    if (submitBtn) {
      submitBtn.disabled = true
    }

    try {
      const response = await fetch(`${API_BASE_URL}/public/rental-inquiry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(payload),
      })

      if (response.status === 204 || response.ok) {
        form.reset()
        setStatus('Vielen Dank — Ihre Mietanfrage wurde gesendet. Wir melden uns bei Ihnen.')
        return
      }

      if (response.status === 429) {
        setStatus('Zu viele Anfragen. Bitte versuchen Sie es in einer Minute erneut.', {
          error: true,
        })
        return
      }

      setStatus(
        'Die Anfrage konnte nicht gesendet werden. Bitte versuchen Sie es später erneut.',
        { error: true },
      )
    } catch {
      setStatus(
        'Keine Verbindung zum Server. Bitte prüfen Sie Ihre Internetverbindung und versuchen Sie es erneut.',
        { error: true },
      )
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false
      }
    }
  })
}

export { validateInquiryFields }

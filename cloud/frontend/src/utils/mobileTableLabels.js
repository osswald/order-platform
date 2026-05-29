function textContent(element) {
  return element?.textContent?.replace(/\s+/g, ' ').trim() || ''
}

function headerLabelsFor(table) {
  return Array.from(table.querySelectorAll('.p-datatable-thead th'))
    .map(textContent)
    .map((label) => label.replace(/\s+/g, ' '))
}

export function applyMobileTableLabels(root = document) {
  const tables = root.querySelectorAll?.('.p-datatable') || []

  tables.forEach((table) => {
    const labels = headerLabelsFor(table)
    if (!labels.length) return

    table.querySelectorAll('.p-datatable-tbody > tr').forEach((row) => {
      Array.from(row.children).forEach((cell, index) => {
        const label = labels[index]
        if (label) {
          cell.setAttribute('data-mobile-label', label)
        } else {
          cell.removeAttribute('data-mobile-label')
        }
      })
    })
  })
}

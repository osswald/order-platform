function createStorage() {
  let data = {}
  return {
    getItem(key) {
      return key in data ? data[key] : null
    },
    setItem(key, value) {
      data[key] = String(value)
    },
    removeItem(key) {
      delete data[key]
    },
    clear() {
      data = {}
    },
  }
}

globalThis.localStorage = createStorage()
globalThis.sessionStorage = createStorage()

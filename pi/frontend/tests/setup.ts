function createStorage(): Storage {
  let data: Record<string, string> = {}
  return {
    get length() {
      return Object.keys(data).length
    },
    key(index: number): string | null {
      return Object.keys(data)[index] ?? null
    },
    getItem(key: string): string | null {
      return key in data ? data[key] : null
    },
    setItem(key: string, value: string): void {
      data[key] = String(value)
    },
    removeItem(key: string): void {
      delete data[key]
    },
    clear(): void {
      data = {}
    },
  }
}

globalThis.localStorage = createStorage()
globalThis.sessionStorage = createStorage()

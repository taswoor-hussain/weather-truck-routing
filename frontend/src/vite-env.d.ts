/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API base URL; defaults to same-origin `/api`. */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

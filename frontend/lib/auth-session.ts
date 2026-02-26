export type AuthRole = "admin" | "org_admin"

export interface StoredAuthSession {
  token: string
  role: AuthRole
  email: string
  organizationName: string
  expiresAt: string
}

const AUTH_KEYS = {
  token: "scdis_auth_token",
  role: "scdis_auth_role",
  email: "scdis_auth_email",
  org: "scdis_auth_org",
  expires: "scdis_auth_expires",
} as const

function hasWindow(): boolean {
  return typeof window !== "undefined"
}

function validRole(role: string | null): role is AuthRole {
  return role === "admin" || role === "org_admin"
}

export function clearAuthSession(): void {
  if (!hasWindow()) {
    return
  }

  for (const storage of [window.sessionStorage, window.localStorage]) {
    storage.removeItem(AUTH_KEYS.token)
    storage.removeItem(AUTH_KEYS.role)
    storage.removeItem(AUTH_KEYS.email)
    storage.removeItem(AUTH_KEYS.org)
    storage.removeItem(AUTH_KEYS.expires)
  }
}

export function persistAuthSession(payload: {
  token: string
  role: AuthRole
  email: string
  organization_name?: string | null
  expires_at: string
}): void {
  if (!hasWindow()) {
    return
  }

  // High-security default: keep session only for this browser tab.
  clearAuthSession()
  window.sessionStorage.setItem(AUTH_KEYS.token, payload.token)
  window.sessionStorage.setItem(AUTH_KEYS.role, payload.role)
  window.sessionStorage.setItem(AUTH_KEYS.email, payload.email)
  window.sessionStorage.setItem(AUTH_KEYS.org, payload.organization_name ?? "")
  window.sessionStorage.setItem(AUTH_KEYS.expires, payload.expires_at)
}

export function readAuthSession(): StoredAuthSession | null {
  if (!hasWindow()) {
    return null
  }

  const token = window.sessionStorage.getItem(AUTH_KEYS.token)
  const role = window.sessionStorage.getItem(AUTH_KEYS.role)
  const email = window.sessionStorage.getItem(AUTH_KEYS.email)
  const organizationName = window.sessionStorage.getItem(AUTH_KEYS.org) ?? ""
  const expiresAt = window.sessionStorage.getItem(AUTH_KEYS.expires)

  if (!token || !validRole(role) || !email || !expiresAt) {
    return null
  }

  return {
    token,
    role,
    email,
    organizationName,
    expiresAt,
  }
}

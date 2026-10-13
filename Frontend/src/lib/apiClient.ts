/**
 * VeriFin Authenticated API Client
 * Automatically attaches multi-tenant JWT credentials and company context headers
 */

const AI_AGENT_BASE = 'http://localhost:8000';
const BACKEND_BASE = 'http://localhost:5000';

export function getAuthHeaders(isFormData: boolean = false): Record<string, string> {
  const token = localStorage.getItem('verifin_token');
  const userJson = localStorage.getItem('verifin_user');
  let companyId = 'comp_techcorp';
  let projectId = 'proj_fleet';

  if (userJson) {
    try {
      const u = JSON.parse(userJson);
      if (u.companyId) companyId = u.companyId;
      if (u.activeProjectId) projectId = u.activeProjectId;
    } catch {
      // ignore
    }
  }

  const headers: Record<string, string> = {
    'X-Company-ID': companyId,
    'X-Project-ID': projectId,
  };

  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
}

export async function fetchWithTenant(url: string, options: RequestInit = {}): Promise<Response> {
  const isFormData = options.body instanceof FormData;
  const authHeaders = getAuthHeaders(isFormData);

  const mergedHeaders = {
    ...authHeaders,
    ...(options.headers as Record<string, string> || {}),
  };

  return fetch(url, {
    ...options,
    headers: mergedHeaders,
  });
}

export { AI_AGENT_BASE, BACKEND_BASE };

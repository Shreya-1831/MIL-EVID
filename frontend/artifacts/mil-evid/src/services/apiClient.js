const baseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

const SESSION_KEY = "mil-evid-session";

/* =========================================================
   SESSION HELPERS
========================================================= */

function getStoredSession() {
  const stored =
    localStorage.getItem(SESSION_KEY) ||
    sessionStorage.getItem(SESSION_KEY);

  if (!stored) {
    return null;
  }

  try {
    return JSON.parse(stored);
  } catch {
    return null;
  }
}

function saveSession(session) {
  if (!session) {
    return;
  }

  const localSession =
    localStorage.getItem(SESSION_KEY);

  const sessionSession =
    sessionStorage.getItem(SESSION_KEY);

  /*
   * Preserve whichever storage was originally
   * selected through "Remember me".
   */
  if (localSession) {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify(session)
    );

    sessionStorage.removeItem(SESSION_KEY);
  } else if (sessionSession) {
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify(session)
    );

    localStorage.removeItem(SESSION_KEY);
  } else {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify(session)
    );
  }
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem(SESSION_KEY);
}

function getAccessToken() {
  const session = getStoredSession();

  return (
    session?.tokens?.access_token ||
    null
  );
}

/* =========================================================
   REFRESH ACCESS TOKEN
========================================================= */

let refreshPromise = null;

async function refreshSession() {
  /*
   * Prevent multiple simultaneous requests from
   * rotating the refresh token multiple times.
   */
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const session = getStoredSession();

    const refreshToken =
      session?.tokens?.refresh_token;

    if (!refreshToken) {
      throw new Error(
        "No refresh token available."
      );
    }

    const response = await fetch(
      `${baseUrl}/api/auth/refresh`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      }
    );

    let data = null;

    try {
      data = await response.json();
    } catch {
      // Empty response.
    }

    if (!response.ok) {
      clearSession();

      const error = new Error(
        data?.detail ||
          data?.error ||
          "Session refresh failed."
      );

      error.status = response.status;
      error.data = data;

      throw error;
    }

    /*
     * Backend returns:
     *
     * {
     *   access_token,
     *   refresh_token,
     *   token_type
     * }
     */
    const updatedSession = {
      ...session,
      tokens: data,
    };

    /*
     * Save the rotated access + refresh tokens.
     */
    saveSession(updatedSession);

    /*
     * Keep AuthContext synchronized with the
     * newly rotated tokens.
     */
    window.dispatchEvent(
      new CustomEvent(
        "mil-evid-session-updated",
        {
          detail: {
            session: updatedSession,
          },
        }
      )
    );

    return updatedSession;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

/* =========================================================
   MAIN API REQUEST
========================================================= */

export async function apiRequest(
  endpoint,
  options = {},
  retry = true
) {
  const {
    method = "GET",
    body,
    authenticated = true,
    accessToken,
  } = options;

  const headers = {};

  if (body !== undefined) {
    headers["Content-Type"] =
      "application/json";
  }

  if (authenticated) {
    const token =
      accessToken || getAccessToken();

    if (token) {
      headers.Authorization =
        `Bearer ${token}`;
    }
  }

  const response = await fetch(
    `${baseUrl}${endpoint}`,
    {
      method,
      headers,
      body:
        body !== undefined
          ? JSON.stringify(body)
          : undefined,
    }
  );

  /* =======================================================
     NO CONTENT
  ======================================================= */

  if (response.status === 204) {
    return null;
  }

  /* =======================================================
     READ RESPONSE
  ======================================================= */

  let data = null;

  try {
    data = await response.json();
  } catch {
    // Empty or non-JSON response.
  }

  /* =======================================================
     ACCESS TOKEN EXPIRED
  ======================================================= */

  if (
    response.status === 401 &&
    authenticated &&
    retry
  ) {
    try {
      const refreshedSession =
        await refreshSession();

      /*
       * Retry the original request exactly once
       * with the new access token.
       */
      return await apiRequest(
        endpoint,
        {
          ...options,
          accessToken:
            refreshedSession.tokens
              .access_token,
        },
        false
      );
    } catch (refreshError) {
      clearSession();

      throw refreshError;
    }
  }

  /* =======================================================
     OTHER ERRORS
  ======================================================= */

  if (!response.ok) {
    const error = new Error(
      data?.detail ||
        data?.error ||
        `Request failed with status ${response.status}`
    );

    error.status = response.status;
    error.data = data;

    throw error;
  }

  return data;
}

/* =========================================================
   API CLIENT
========================================================= */

export const apiClient = {
  baseUrl,

  async listAnalyses() {
    const response = await apiRequest(
      "/api/analysis"
    );

    return response?.analyses ?? [];
  },

  async getAnalysis(id) {
    return apiRequest(
      `/api/analysis/${id}`
    );
  },

  async deleteAnalysis(id) {
    return apiRequest(
      `/api/analysis/${id}`,
      {
        method: "DELETE",
      }
    );
  },

  async runAnalysis(payload) {
    return apiRequest(
      "/api/analysis",
      {
        method: "POST",
        body: payload,
      }
    );
  },

  async listEvidence({
    source,
    limit = 50,
    offset = 0,
  } = {}) {
    const params = new URLSearchParams();

    params.set("limit", String(limit));
    params.set("offset", String(offset));

    if (source) {
      params.set("source", source);
    }

    return apiRequest(
      `/api/evidence?${params.toString()}`
    );
  },

  async getEvidence(id) {
    return apiRequest(
      `/api/evidence/${id}`
    );
  },

  async listEvidenceSources() {
    return apiRequest(
      "/api/evidence/sources/list"
    );
  },
  async getCurrentUser() {
    return apiRequest("/api/auth/me");
  },
};
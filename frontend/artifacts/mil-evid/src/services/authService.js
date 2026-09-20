import { apiRequest } from "./apiClient";

const SESSION_KEY = "mil-evid-session";

function getStorage(remember = true) {
  return remember ? localStorage : sessionStorage;
}

function getOtherStorage(remember = true) {
  return remember ? sessionStorage : localStorage;
}

function saveSession(authResponse, remember = true) {
  const session = {
    user: authResponse.user,
    tokens: authResponse.tokens,
  };

  const storage = getStorage(remember);
  const otherStorage = getOtherStorage(remember);

  storage.setItem(
    SESSION_KEY,
    JSON.stringify(session)
  );

  otherStorage.removeItem(SESSION_KEY);

  return session;
}

export function readSession() {
  const stored =
    localStorage.getItem(SESSION_KEY) ||
    sessionStorage.getItem(SESSION_KEY);

  if (!stored) {
    return null;
  }

  try {
    return JSON.parse(stored);
  } catch {
    clearSession();
    return null;
  }
}

export async function loginUser({
  email,
  password,
  remember = true,
}) {
  const response = await apiRequest(
    "/api/auth/login",
    {
      method: "POST",
      body: {
        email,
        password,
      },
      authenticated: false,
    }
  );

  return saveSession(
    response,
    remember
  );
}

export async function registerUser({
  full_name,
  email,
  password,
  remember = true,
}) {
  const response = await apiRequest(
    "/api/auth/register",
    {
      method: "POST",
      body: {
        full_name,
        email,
        password,
      },
      authenticated: false,
    }
  );

  return saveSession(
    response,
    remember
  );
}

export async function getCurrentUser(
  accessToken
) {
  return apiRequest(
    "/api/auth/me",
    {
      method: "GET",
      accessToken,
    }
  );
}

export async function refreshAccessToken(
  refreshToken
) {
  return apiRequest(
    "/api/auth/refresh",
    {
      method: "POST",
      body: {
        refresh_token: refreshToken,
      },
      authenticated: false,
    }
  );
}

export async function logoutUser(
  refreshToken
) {
  return apiRequest(
    "/api/auth/logout",
    {
      method: "POST",
      body: {
        refresh_token: refreshToken,
      },
      authenticated: false,
    }
  );
}

export function clearSession() {
  localStorage.removeItem(
    SESSION_KEY
  );

  sessionStorage.removeItem(
    SESSION_KEY
  );
}
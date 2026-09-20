const SESSION_KEY = 'mil-evid-session';
const USERS_KEY = 'mil-evid-users';

export function readSession() {
  const stored = localStorage.getItem(SESSION_KEY) || sessionStorage.getItem(SESSION_KEY);
  if (!stored) return null;
  try { return JSON.parse(stored); } catch { clearSession(); return null; }
}

export function createSession({ email, name, role = 'Analyst', remember = false }) {
  const session = { name: name || email.split('@')[0].replace(/[._-]/g, ' '), email, role, signedInAt: new Date().toISOString() };
  const storage = remember ? localStorage : sessionStorage;
  storage.setItem(SESSION_KEY, JSON.stringify(session));
  (remember ? sessionStorage : localStorage).removeItem(SESSION_KEY);
  return session;
}

export function saveRegisteredUser({ name, email }) {
  const users = JSON.parse(localStorage.getItem(USERS_KEY) || '[]');
  localStorage.setItem(USERS_KEY, JSON.stringify([...users, { name, email }]));
  return createSession({ name, email, role: 'Analyst', remember: true });
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem(SESSION_KEY);
}
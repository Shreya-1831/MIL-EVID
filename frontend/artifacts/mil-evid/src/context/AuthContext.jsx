import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { clearSession, createSession, readSession, saveRegisteredUser } from '../services/authService';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);
  useEffect(() => {
    setUser(readSession());
    setInitializing(false);
  }, []);
  const login = async ({ email, remember }) => {
    const session = createSession({ email, role: 'Senior Analyst', remember });
    setUser(session);
    return session;
  };
  const register = async ({ name, email }) => {
    const session = saveRegisteredUser({ name, email });
    setUser(session);
    return session;
  };
  const logout = () => { setUser(null); clearSession(); };
  const value = useMemo(() => ({ user, initializing, login, register, logout }), [user, initializing]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { return useContext(AuthContext); }
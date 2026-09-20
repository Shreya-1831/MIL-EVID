import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  clearSession,
  getCurrentUser,
  loginUser,
  logoutUser,
  readSession,
  refreshAccessToken,
  registerUser,
} from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [initializing, setInitializing] = useState(true);

  // Restore an existing session when the application starts.
  useEffect(() => {
    async function restoreSession() {
      const storedSession = readSession();

      if (!storedSession?.tokens?.access_token) {
        setInitializing(false);
        return;
      }

      try {
        // Validate the stored access token.
        const currentUser = await getCurrentUser(
          storedSession.tokens.access_token
        );

        const restoredSession = {
          ...storedSession,
          user: currentUser,
        };

        setSession(restoredSession);
        setUser(currentUser);
      } catch (error) {
        console.warn(
          "Stored access token is invalid or expired."
        );

        // Try the refresh token.
        const refreshToken =
          storedSession.tokens?.refresh_token;

        if (!refreshToken) {
          clearSession();
          setUser(null);
          setSession(null);
          setInitializing(false);
          return;
        }

        try {
          const tokens = await refreshAccessToken(
            refreshToken
          );

          const refreshedSession = {
            ...storedSession,
            tokens,
          };

          // Validate the newly refreshed access token.
          const currentUser = await getCurrentUser(
            tokens.access_token
          );

          refreshedSession.user = currentUser;

          // Preserve localStorage/sessionStorage choice.
          const storage = localStorage.getItem(
            "mil-evid-session"
          )
            ? localStorage
            : sessionStorage;

          storage.setItem(
            "mil-evid-session",
            JSON.stringify(refreshedSession)
          );

          setSession(refreshedSession);
          setUser(currentUser);
        } catch (refreshError) {
          console.error(
            "Unable to refresh authentication session:",
            refreshError
          );

          clearSession();
          setUser(null);
          setSession(null);
        }
      } finally {
        setInitializing(false);
      }
    }

    restoreSession();
  }, []);

  // Real backend login.
  async function login({
    email,
    password,
    remember = true,
  }) {
    const newSession = await loginUser({
      email,
      password,
      remember,
    });

    setSession(newSession);
    setUser(newSession.user);

    return newSession;
  }

  // Real backend registration.
  async function register({
    name,
    email,
    password,
    remember = true,
  }) {
    const newSession = await registerUser({
      full_name: name,
      email,
      password,
      remember,
    });

    setSession(newSession);
    setUser(newSession.user);

    return newSession;
  }

  // Real backend logout.
  async function logout() {
    const refreshToken =
      session?.tokens?.refresh_token;

    try {
      if (refreshToken) {
        await logoutUser(refreshToken);
      }
    } catch (error) {
      // Local session should still be cleared.
      console.warn(
        "Backend logout request failed:",
        error
      );
    } finally {
      clearSession();
      setUser(null);
      setSession(null);
    }
  }

  const value = useMemo(
    () => ({
      user,
      session,
      initializing,
      login,
      register,
      logout,
    }),
    [user, session, initializing]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
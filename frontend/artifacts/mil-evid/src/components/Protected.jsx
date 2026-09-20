import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

import Shell from "./Shell";

function Protected({ children }) {
  const { user, initializing } = useAuth();

  const location = useLocation();

  /*
   * AuthContext is still checking the stored session.
   * Do not redirect while authentication is initializing.
   */
  if (initializing) {
    return (
      <div className="min-h-[100dvh] bg-background p-8">
        <div className="mx-auto max-w-xl animate-pulse space-y-4">
          <div className="h-3 w-28 bg-muted" />
          <div className="h-12 w-2/3 bg-muted" />
          <div className="h-32 bg-muted" />
        </div>
      </div>
    );
  }

  /*
   * Authentication finished but there is no logged-in user.
   */
  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: location.pathname,
        }}
      />
    );
  }

  /*
   * Authenticated user can access the protected application.
   */
  return <Shell>{children}</Shell>;
}

export default Protected;
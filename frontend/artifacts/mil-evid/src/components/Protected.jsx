import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Shell from "./Shell";

function Protected({ children }) {
  const { user, initializing } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!initializing && !user) navigate("/login");
  }, [initializing, user, navigate]);

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

  return user ? <Shell>{children}</Shell> : null;
}

export default Protected;
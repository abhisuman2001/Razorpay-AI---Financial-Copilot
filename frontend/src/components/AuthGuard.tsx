/**
 * AuthGuard — wraps all protected routes.
 *
 * Strategy: We treat the presence of the localStorage user-profile key as a
 * "soft session indicator". For this prototype there is no real auth backend
 * yet, so we use a flag written by beginSession() and cleared by endSession().
 *
 * When a real auth backend is in place, replace the localStorage check with
 * a lightweight GET /api/auth/me call (useQuery with retry:false) and redirect
 * on 401/403.
 */
import { Navigate, Outlet } from "react-router-dom";

const SESSION_FLAG = "razorpay-ai-session-active";

/** Called by beginSession() to mark the session as live. */
export function markSessionActive(): void {
  try {
    window.sessionStorage.setItem(SESSION_FLAG, "1");
  } catch {
    // non-fatal — storage may be unavailable in some private-browsing contexts
  }
}

/** Called by endSession() to clear the session marker. */
export function clearSessionMark(): void {
  try {
    window.sessionStorage.removeItem(SESSION_FLAG);
  } catch {
    // non-fatal
  }
}

function isSessionActive(): boolean {
  try {
    return window.sessionStorage.getItem(SESSION_FLAG) === "1";
  } catch {
    return false;
  }
}

export default function AuthGuard() {
  if (!isSessionActive()) {
    return <Navigate to="/landing" replace />;
  }
  return <Outlet />;
}

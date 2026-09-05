// Session boundary: auth is an httpOnly cookie the backend owns; the frontend's one
// duty is wiping the react-query cache so one account's data never renders for the next.
import { queryClient } from "./queryClient";
import { apiPost } from "./api";
import { markSessionActive, clearSessionMark } from "@/components/AuthGuard";

// Call after every successful login/signup.
export function beginSession(): void {
  queryClient.clear();
  markSessionActive();
}

// Call from every sign-out control; the hard redirect resets all in-memory state.
export async function endSession(redirectTo: string = "/landing"): Promise<void> {
  try {
    await apiPost("/auth/logout");
  } finally {
    queryClient.clear();
    clearSessionMark();
    window.location.assign(redirectTo);
  }
}

/**
 * Lightweight user profile context.
 * Profile is stored in localStorage so edits survive page reloads for this
 * demo (no real auth / backend persistence).
 */
import { createContext, useContext, useState, type ReactNode } from "react";

export interface UserProfile {
  name: string;
  role: string;
  email: string;
  phone: string;
  company: string;
  department: string;
  location: string;
  bio: string;
  avatarUrl: string;
}

const STORAGE_KEY = "razorpay-ai-user-profile";

const DEFAULT_PROFILE: UserProfile = {
  name: "Aarav Mehta",
  role: "Finance lead",
  email: "aarav.mehta@northstar.in",
  phone: "+91 98765 43210",
  company: "Northstar Commerce Pvt Ltd",
  department: "Finance & Accounts",
  location: "Mumbai, Maharashtra",
  bio: "Finance lead with 8+ years of experience in financial operations, cash flow management, and payment reconciliation.",
  avatarUrl: "https://images.pexels.com/photos/27086922/pexels-photo-27086922.jpeg",
};

function loadProfile(): UserProfile {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...DEFAULT_PROFILE, ...JSON.parse(raw) };
  } catch {
    // fall through to default
  }
  return DEFAULT_PROFILE;
}

interface UserProfileContextValue {
  profile: UserProfile;
  updateProfile: (updates: Partial<UserProfile>) => void;
}

const UserProfileContext = createContext<UserProfileContextValue | null>(null);

export function UserProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<UserProfile>(loadProfile);

  const updateProfile = (updates: Partial<UserProfile>) => {
    const next = { ...profile, ...updates };
    setProfile(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // non-fatal
    }
  };

  return (
    <UserProfileContext.Provider value={{ profile, updateProfile }}>
      {children}
    </UserProfileContext.Provider>
  );
}

export function useUserProfile(): UserProfileContextValue {
  const ctx = useContext(UserProfileContext);
  if (!ctx) throw new Error("useUserProfile must be used inside <UserProfileProvider>");
  return ctx;
}

/** Returns the user's initials (up to 2 chars) for avatar fallback */
export function getInitials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

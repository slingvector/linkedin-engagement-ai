import { create } from 'zustand';

interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  profile_picture_url: string | null;
  linkedin_id: string;
  subscription_tier: string;
  write_flow_connected: boolean;
}

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  setUser: (user: UserProfile) => void;
  logout: () => void;
}

const TOKEN_KEY = 'linkedin_copilot_token';

// Rehydrate from localStorage on store init
const storedToken = typeof window !== 'undefined'
  ? localStorage.getItem(TOKEN_KEY)
  : null;

export const useAuthStore = create<AuthState>((set) => ({
  token: storedToken,
  user: null,
  isAuthenticated: !!storedToken,

  setToken: (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    set({ token, isAuthenticated: true });
  },

  setUser: (user: UserProfile) => {
    set({ user });
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ token: null, user: null, isAuthenticated: false });
  },
}));

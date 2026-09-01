"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api";

interface User {
  id: string;
  username: string;
  email: string;
  roles: string[];
  scopes: string[];
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
  setTokens: (access: string, refresh: string) => void;
  fetchUser: () => Promise<void>;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (username: string, password: string) => {
        const response = await api.post("/auth/login", { username, password });
        const { access_token, refresh_token } = response.data;
        set({
          accessToken: access_token,
          refreshToken: refresh_token,
          isAuthenticated: true,
        });
        await get().fetchUser();
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) return;

        try {
          const response = await api.post("/auth/refresh", { refresh_token: refreshToken });
          const { access_token, refresh_token: newRefreshToken } = response.data;
          set({ accessToken: access_token, refreshToken: newRefreshToken });
        } catch {
          get().logout();
        }
      },

      setTokens: (access: string, refresh: string) => {
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true });
      },

      fetchUser: async () => {
        const { accessToken } = get();
        if (!accessToken) {
          set({ user: null, isAuthenticated: false, isLoading: false });
          return;
        }

        try {
          const response = await api.get("/auth/me");
          set({ user: response.data, isAuthenticated: true, isLoading: false });
        } catch {
          set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false, isLoading: false });
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken) {
          state.fetchUser();
        } else {
          useAuth.setState({ isLoading: false });
        }
      },
    }
  )
);

export const getAccessToken = () => useAuth.getState().accessToken;
export const refreshAccessToken = () => useAuth.getState().refreshAccessToken();
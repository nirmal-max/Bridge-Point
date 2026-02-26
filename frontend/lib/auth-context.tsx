"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import { api } from "@/lib/api";
import { User } from "@/lib/types";

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    phone: string;
    password: string;
    full_name: string;
    labor_category?: string;
    skills?: string[];
    city?: string;
    bio?: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const setAuth = useCallback((t: string, u: User) => {
    localStorage.setItem("bp_token", t);
    localStorage.setItem("bp_user", JSON.stringify(u));
    setToken(t);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("bp_token");
    localStorage.removeItem("bp_user");
    localStorage.removeItem("bp_active_role"); // Clean up legacy key
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    const savedToken = localStorage.getItem("bp_token");
    const savedUser = localStorage.getItem("bp_user");

    if (savedToken && savedUser) {
      setToken(savedToken);
      const parsedUser = JSON.parse(savedUser) as User;
      setUser(parsedUser);

      api
        .getMe()
        .then((u) => {
          setUser(u);
          localStorage.setItem("bp_user", JSON.stringify(u));
        })
        .catch(() => logout());
    }
    setLoading(false);
  }, [logout]);

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password);
    setAuth(res.access_token, res.user);
  };

  const register = async (data: {
    email: string;
    phone: string;
    password: string;
    full_name: string;
    labor_category?: string;
    skills?: string[];
    city?: string;
    bio?: string;
  }) => {
    const res = await api.register({ ...data, role: "both" });
    setAuth(res.access_token, res.user);
  };

  return (
    <AuthContext.Provider
      value={{ user, token, loading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import api from "../lib/api";
import type { UserProfile, AuthResponse } from "../lib/types";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("access_token")
  );
  const [isLoading, setIsLoading] = useState(true);

  // On mount, check if we have a stored token and fetch user
  useEffect(() => {
    const loadUser = async () => {
      const storedToken = localStorage.getItem("access_token");
      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      try {
        const resp = await api.get<UserProfile>("/auth/me");
        setUser(resp.data);
        setToken(storedToken);
      } catch {
        localStorage.removeItem("access_token");
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadUser();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const resp = await api.post<AuthResponse>("/auth/login", {
      email,
      password,
    });

    const { access_token, user: userData } = resp.data;
    localStorage.setItem("access_token", access_token);
    setToken(access_token);
    setUser(userData);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    const resp = await api.post<AuthResponse>("/auth/register", {
      email,
      password,
    });

    const { access_token, user: userData } = resp.data;
    if (access_token) {
      localStorage.setItem("access_token", access_token);
      setToken(access_token);
    }
    setUser(userData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, token, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

/**
 * API Configuration for Watcha.
 * Automatically resolves the correct backend API URL based on environment
 * and hostname — completely transparent to the user.
 */

export const DEFAULT_PROD_API_URL = "https://watcha-backend.onrender.com";
export const DEFAULT_LOCAL_API_URL = "http://localhost:8000";

/**
 * Resolves the active backend base URL without a trailing slash.
 */
export function getApiBaseUrl(): string {
  // 1. If a non-localhost VITE_API_URL was injected at build time, use it
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === "string" && envUrl.trim()) {
    const cleanEnv = envUrl.trim().replace(/\/+$/, "");
    if (!cleanEnv.includes("localhost") && !cleanEnv.includes("127.0.0.1")) {
      return cleanEnv;
    }
  }

  // 2. If browsing locally on localhost or 127.0.0.1, route to local backend
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return (envUrl && envUrl.trim().replace(/\/+$/, "")) || DEFAULT_LOCAL_API_URL;
    }
  }

  // 3. Default for hosted production (e.g. *.vercel.app)
  return DEFAULT_PROD_API_URL;
}

/**
 * API Configuration for Watcha.
 * Automatically resolves the correct backend API URL based on environment,
 * hostname, and user preferences.
 */

// Default Render production backend URL
export const DEFAULT_PROD_API_URL = "https://watcha-backend.onrender.com";
export const DEFAULT_LOCAL_API_URL = "http://localhost:8000";

/**
 * Resolves the active backend base URL without a trailing slash.
 */
export function getApiBaseUrl(): string {
  // 1. Check for manual user override in localStorage
  if (typeof window !== "undefined") {
    const savedUrl = localStorage.getItem("watcha_api_url");
    if (savedUrl && savedUrl.trim()) {
      return savedUrl.trim().replace(/\/+$/, "");
    }
  }

  // 2. Check if a non-localhost VITE_API_URL was injected at build time
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === "string" && envUrl.trim()) {
    const cleanEnv = envUrl.trim().replace(/\/+$/, "");
    // If the build variable is explicitly pointing to an external domain, use it
    if (!cleanEnv.includes("localhost") && !cleanEnv.includes("127.0.0.1")) {
      return cleanEnv;
    }
  }

  // 3. Inspect browser location:
  // If running locally in dev (localhost or 127.0.0.1), route to local backend
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return (envUrl && envUrl.trim().replace(/\/+$/, "")) || DEFAULT_LOCAL_API_URL;
    }
  }

  // 4. Default for hosted production (e.g. *.vercel.app)
  return DEFAULT_PROD_API_URL;
}

/**
 * Update the user's manual API URL override.
 */
export function setCustomApiUrl(url: string): void {
  if (typeof window !== "undefined") {
    const clean = url.trim().replace(/\/+$/, "");
    if (!clean || clean === DEFAULT_PROD_API_URL || clean === DEFAULT_LOCAL_API_URL) {
      localStorage.removeItem("watcha_api_url");
    } else {
      localStorage.setItem("watcha_api_url", clean);
    }
  }
}

/**
 * Clear custom API URL and revert to automatic discovery.
 */
export function resetApiUrl(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("watcha_api_url");
  }
}

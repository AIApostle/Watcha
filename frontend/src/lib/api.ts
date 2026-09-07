import axios from "axios";
import { getApiBaseUrl } from "./apiConfig";

const api = axios.create({
  baseURL: `${getApiBaseUrl()}/api`,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach auth token and ensure up-to-date baseURL on every request
api.interceptors.request.use((config) => {
  config.baseURL = `${getApiBaseUrl()}/api`;
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 — redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;

import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Automatically attach JWT token to every API request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("aegisdesk_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// Handle expired/invalid JWT tokens
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      !String(error.config?.url || "").includes("/api/auth/login")
    ) {
      localStorage.removeItem("aegisdesk_token");
      localStorage.removeItem("aegisdesk_user");

      window.dispatchEvent(new Event("aegisdesk:unauthorized"));
    }

    return Promise.reject(error);
  },
);

export default api;
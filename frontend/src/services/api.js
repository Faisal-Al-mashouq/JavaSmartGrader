import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000", // future FastAPI
});

// attach token automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/** Safe string for UI; FastAPI often returns `detail` as a string or a list of `{ msg, ... }`. */
export function getApiErrorMessage(error, fallback = "Something went wrong.") {
  const detail = error?.response?.data?.detail;
  if (detail == null) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item != null && typeof item === "object" && "msg" in item) {
        return String(item.msg);
      }
      return typeof item === "string" ? item : JSON.stringify(item);
    });
    return parts.filter(Boolean).join(" ") || fallback;
  }
  if (typeof detail === "object" && detail != null && "msg" in detail) {
    return String(detail.msg);
  }
  try {
    return JSON.stringify(detail);
  } catch {
    return fallback;
  }
}

export default api;

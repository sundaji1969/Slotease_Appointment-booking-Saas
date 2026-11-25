import axios, { AxiosError } from "axios";

import { clearToken, getToken } from "../lib/auth";
import type { ApiError } from "./types";

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: API_URL, timeout: 15000 });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token && !config.url?.startsWith("/public") && !config.url?.startsWith("/auth")) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error: AxiosError) => {
    const url = error.config?.url ?? "";
    if (error.response?.status === 401 && !url.startsWith("/auth") && !url.startsWith("/public")) {
      clearToken();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);

export function apiError(err: unknown): ApiError & { status?: number } {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as Partial<ApiError> | undefined;
    return {
      status: err.response?.status,
      error: data?.error ?? "NETWORK_ERROR",
      message: data?.message ?? "Could not reach the server. Check your connection and try again.",
    };
  }
  return { error: "UNKNOWN", message: "Something went wrong" };
}

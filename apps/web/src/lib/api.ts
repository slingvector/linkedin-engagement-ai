import axios from 'axios';
import { useAuthStore } from '@/lib/store';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
const API_V2_URL = process.env.NEXT_PUBLIC_API_V2_URL || '/api/v2';

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const apiV2 = axios.create({
  baseURL: API_V2_URL,
  headers: { 'Content-Type': 'application/json' },
});

// --- Auth interceptors (applied to both clients) ---

function attachAuthInterceptors(client: typeof api) {
  // Request: attach JWT bearer token
  client.interceptors.request.use((config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  });

  // Response: on 401 → clear token and redirect to login
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        useAuthStore.getState().logout();
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
      }
      return Promise.reject(error);
    }
  );
}

attachAuthInterceptors(api);
attachAuthInterceptors(apiV2);

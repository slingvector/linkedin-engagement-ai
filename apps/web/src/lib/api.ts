import axios from 'axios';

// Get API URL from env, default to local Core API
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const API_V2_URL = process.env.NEXT_PUBLIC_API_V2_URL || 'http://localhost:8000/api/v2';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiV2 = axios.create({
  baseURL: API_V2_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Since we mock login initially, we will assume requests are unauthenticated
// or use a mock JWT/user_id depending on how we handle auth locally.
// For now, let's just create the client.

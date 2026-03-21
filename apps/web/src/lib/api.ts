import axios from 'axios';

// Get API URL from env, default to local Core API
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // If we were handling real cookies in this POC: 
  // withCredentials: true
});

// Since we mock login initially, we will assume requests are unauthenticated
// or use a mock JWT/user_id depending on how we handle auth locally.
// For now, let's just create the client.

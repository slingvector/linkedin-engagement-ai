'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';

type Status = 'loading' | 'success' | 'error';

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<Status>('loading');
  const [message, setMessage] = useState('Connecting your LinkedIn account...');

  const { setToken, setUser } = useAuthStore();

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');

    if (error) {
      setStatus('error');
      setMessage('LinkedIn declined the request. Please try again.');
      return;
    }

    if (!code || !state) {
      setStatus('error');
      setMessage('Missing authorization parameters.');
      return;
    }

    const handleCallback = async () => {
      try {
        // Exchange code for JWT
        const tokenRes = await api.get('/auth/linkedin/callback', {
          params: { code, state },
        });
        const { access_token } = tokenRes.data;

        // Store token first so the /auth/me request is authorized
        setToken(access_token);

        // Load user profile
        const meRes = await api.get('/auth/me');
        setUser(meRes.data);

        setStatus('success');
        setMessage('Connected! Taking you in...');

        // Short delay so the success state is visible, then redirect
        setTimeout(() => router.push('/'), 1200);
      } catch (err: unknown) {
        console.error('OAuth callback error:', err);
        setStatus('error');
        setMessage(
          'Authentication failed. Please go back and try again.'
        );
      }
    };

    handleCallback();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="text-center space-y-4 max-w-sm">
        {status === 'loading' && (
          <>
            <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto" />
            <p className="text-sm text-muted-foreground">{message}</p>
          </>
        )}
        {status === 'success' && (
          <>
            <CheckCircle className="w-10 h-10 text-green-500 mx-auto" />
            <p className="text-sm text-muted-foreground">{message}</p>
          </>
        )}
        {status === 'error' && (
          <>
            <XCircle className="w-10 h-10 text-destructive mx-auto" />
            <p className="text-sm text-muted-foreground">{message}</p>
            <a
              href="/login"
              className="inline-block text-sm text-primary underline underline-offset-4"
            >
              Back to login
            </a>
          </>
        )}
      </div>
    </div>
  );
}

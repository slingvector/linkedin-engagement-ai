'use client';

import { useState } from 'react';
import { Linkedin, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLinkedInLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get('/auth/linkedin');
      const { auth_url } = res.data;
      // Redirect the browser to LinkedIn's consent screen
      window.location.href = auth_url;
    } catch (err) {
      setError('Failed to connect. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-8">
        {/* Logo / App Name */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 mb-2">
            <Linkedin className="w-7 h-7 text-primary" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">LinkedIn Copilot</h1>
          <p className="text-sm text-muted-foreground">
            AI-powered content &amp; engagement automation
          </p>
        </div>

        {/* Sign-in card */}
        <div className="border rounded-xl p-6 space-y-4 bg-card shadow-sm">
          <p className="text-sm text-center text-muted-foreground">
            Connect your LinkedIn account to get started.
          </p>

          <button
            onClick={handleLinkedInLogin}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#0A66C2] hover:bg-[#004182] text-white font-medium text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Linkedin className="w-4 h-4" />
            )}
            {loading ? 'Redirecting...' : 'Sign in with LinkedIn'}
          </button>

          {error && (
            <p className="text-xs text-destructive text-center">{error}</p>
          )}
        </div>

        <p className="text-xs text-center text-muted-foreground">
          Your LinkedIn credentials are never stored by this app.
          Authentication is handled directly by LinkedIn OAuth 2.0.
        </p>
      </div>
    </div>
  );
}

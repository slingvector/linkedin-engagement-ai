'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { Toaster } from '@/components/ui/sonner';
import { GlobalSearch } from '@/components/GlobalSearch';
import { useAuthStore } from '@/lib/store';
import { api } from '@/lib/api';

// Routes that don't require authentication
const PUBLIC_ROUTES = ['/login', '/auth/callback'];

export default function RootLayoutClient({
  children,
}: {
  children: React.ReactNode;
}) {
  const [queryClient] = useState(() => new QueryClient());
  const pathname = usePathname();
  const router = useRouter();
  const { token, isAuthenticated, setUser, logout } = useAuthStore();
  const [checking, setChecking] = useState(true);

  const isPublicRoute = PUBLIC_ROUTES.some((r) => pathname?.startsWith(r));

  useEffect(() => {
    if (isPublicRoute) {
      setChecking(false);
      return;
    }

    if (!token) {
      router.replace('/login');
      setChecking(false);
      return;
    }

    // Validate token with backend and load user profile
    api
      .get('/auth/me')
      .then((res) => {
        setUser(res.data);
        setChecking(false);
      })
      .catch(() => {
        // Token invalid or expired
        logout();
        router.replace('/login');
        setChecking(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  // Show spinner while validating auth (only on protected routes)
  if (!isPublicRoute && checking) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Public routes render without sidebar/layout
  if (isPublicRoute) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
        <Toaster />
      </QueryClientProvider>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex bg-background min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">{children}</main>
        <GlobalSearch />
        <Toaster />
      </div>
    </QueryClientProvider>
  );
}

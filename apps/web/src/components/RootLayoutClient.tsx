"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Toaster } from "@/components/ui/sonner";
import { GlobalSearch } from "@/components/GlobalSearch";

export default function RootLayoutClient({
  children,
}: {
  children: React.ReactNode;
}) {
  const [queryClient] = useState(() => new QueryClient());

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

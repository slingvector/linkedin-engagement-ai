"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { 
  Building2, 
  MapPin, 
  Search, 
  Sparkles,
  Link as LinkIcon,
  Globe,
  RadioTower,
  Briefcase
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

async function fetchAbmSignals() {
  const token = localStorage.getItem("access_token");
  const res = await fetch("http://192.168.31.242:8000/api/v1/enterprise/signals", {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to fetch enterprise signals");
  const json = await res.json();
  return json.data;
}

export default function AbmRadarPage() {
  const { data: accountsData = [], isLoading } = useQuery({
    queryKey: ["enterprise", "signals"],
    queryFn: fetchAbmSignals,
    refetchInterval: 10000 // Poll every 10s for new corporate triggers
  });

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">ABM Signal Radar</h2>
          <p className="text-muted-foreground">Monitoring active target accounts for enterprise buying triggers (Funding, Execution, News).</p>
        </div>
        <div className="flex space-x-2">
           <Button variant="outline"><Search className="mr-2 h-4 w-4" /> Search Organizations</Button>
           <Button className="bg-indigo-600 hover:bg-indigo-700">
             <RadioTower className="mr-2 h-4 w-4" /> Add Tracking Domains
           </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
           {[1,2,3].map(i => <div key={i} className="h-64 rounded-xl bg-muted animate-pulse"></div>)}
        </div>
      ) : accountsData.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-24 text-center border rounded-xl border-dashed">
            <Building2 className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
            <h3 className="text-lg font-semibold">No Target Accounts Found</h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-2">
              The ABM Seeder is scanning designated Crunchbase and LinkedIn domains for signals matching your Ideal Customer Profile.
            </p>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {accountsData.map((item: any) => {
                const acct = item.account;
                const signals = item.signals || [];
                
                return (
                 <Card key={acct.id} className="group relative overflow-hidden transition-all hover:shadow-lg border-indigo-100 dark:border-indigo-900 shadow-indigo-100/20">
                    <CardHeader className="bg-gradient-to-br from-indigo-50/50 to-white dark:from-indigo-950/20 dark:to-background border-b pb-4">
                        <div className="flex justify-between items-start mb-2">
                            <Badge variant="outline" className="bg-background text-[10px] tracking-wider font-semibold uppercase">
                                {acct.industry || "SaaS"}
                            </Badge>
                            <Badge className="bg-indigo-100 text-indigo-700 hover:bg-indigo-100 border-indigo-200">
                                {acct.abm_status}
                            </Badge>
                        </div>
                        <CardTitle className="text-xl font-bold flex items-center gap-2">
                            <Building2 className="w-5 h-5 text-indigo-500" />
                            {acct.company_name}
                        </CardTitle>
                        <CardDescription className="flex items-center gap-4 text-xs mt-1">
                            <span className="flex items-center gap-1"><Briefcase className="w-3 h-3"/> {acct.employee_count} Emp.</span>
                            <span className="flex items-center gap-1"><Globe className="w-3 h-3"/> {acct.domain}</span>
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-4">
                        <div className="space-y-4">
                            <div className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
                                <RadioTower className="w-4 h-4 text-indigo-500"/>
                                Active Signals ({signals.length})
                            </div>
                            
                            {signals.length === 0 ? (
                                <p className="text-xs text-muted-foreground italic">Monitoring for triggers...</p>
                            ) : (
                                <div className="space-y-3">
                                    {signals.slice(0, 2).map((sig: any) => (
                                       <div key={sig.id} className="relative pl-4 border-l-2 border-indigo-200 dark:border-indigo-800">
                                            <div className="absolute w-2 h-2 rounded-full bg-indigo-500 -left-[5px] top-1.5 ring-2 ring-background"></div>
                                            <div className="text-xs font-semibold uppercase text-indigo-600 dark:text-indigo-400 mb-1 tracking-wider">
                                                {sig.signal_type.replace("_", " ")}
                                            </div>
                                            <div className="text-sm text-foreground/90 leading-snug">
                                                {sig.signal_description}
                                            </div>
                                            <div className="text-[10px] text-muted-foreground mt-1">
                                                {formatDistanceToNow(new Date(sig.discovered_at))} ago
                                            </div>
                                       </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        
                        <div className="mt-5 pt-4 border-t flex gap-2">
                            <Button className="w-full bg-indigo-600 hover:bg-indigo-700" size="sm">
                                <Sparkles className="w-4 h-4 mr-2" /> Launch ABM Campaign
                            </Button>
                        </div>
                    </CardContent>
                 </Card>
                );
            })}
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useState, useEffect } from "react";
import { formatDistanceToNow } from "date-fns";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  Building2, 
  MessageSquare, 
  UserCircle, 
  Target, 
  Send,
  Zap,
  CheckCircle2,
  Clock
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

// --- API LAYER ---
async function fetchProspects() {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/sales/prospects`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to fetch prospects");
  const json = await res.json();
  return json.data;
}

async function classifyIntent(prospectId: string, prospectName: string, headline: string, buyingSignal: string) {
  const token = localStorage.getItem("access_token");
  const res = await fetch("http://192.168.31.242:8001/webhooks/sales/classify-intent", {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "X-AI-API-Key": "test-ai-key-123" 
    },
    body: JSON.stringify({
      prospect_name: prospectName,
      headline: headline,
      buying_signal: buyingSignal
    })
  });
  if (!res.ok) throw new Error("Failed to classify intent");
  return res.json();
}

async function draftDMs(prospectName: string, headline: string, buyingSignal: string) {
  const token = localStorage.getItem("access_token");
  const res = await fetch("http://192.168.31.242:8001/webhooks/sales/draft-dm", {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "X-AI-API-Key": "test-ai-key-123" 
    },
    body: JSON.stringify({
      prospect_name: prospectName,
      headline: headline,
      buying_signal: buyingSignal,
      my_company_context: "We are building an AI-native CRM that automates lead detection and LinkedIn outreach personalization."
    })
  });
  if (!res.ok) throw new Error("Failed to draft DMs");
  return res.json();
}

async function updateConversationStatus(prospectId: string, status: string) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/sales/prospects/${prospectId}/status`, {
    method: "PUT",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}` 
    },
    body: JSON.stringify({ status })
  });
  if (!res.ok) throw new Error("Failed to update status");
  return res.json();
}

// --- COMPONENTS ---
export default function LeadInboxPage() {
  const queryClient = useQueryClient();
  const [selectedProspectId, setSelectedProspectId] = useState<string | null>(null);
  
  // Queries
  const { data: prospects = [], isLoading } = useQuery({
    queryKey: ["prospects"],
    queryFn: fetchProspects,
    refetchInterval: 5000 // Poll for new leads created by seeder
  });

  const selectedProspect = prospects.find((p: any) => p.id === selectedProspectId);

  // Mutations
  const intentMutation = useMutation({
    mutationFn: (p: any) => classifyIntent(p.id, p.name, p.headline, p.buying_signal),
  });

  const dmDraftMutation = useMutation({
    mutationFn: (p: any) => draftDMs(p.name, p.headline, p.buying_signal),
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) => updateConversationStatus(id, status),
    onSuccess: () => {
      // In a real app we might toast here
    }
  });

  // Effects
  useEffect(() => {
    // When a prospect is selected, fire off the AI requests if they haven't been scored yet locally.
    // For pure mockup simulation, we just fire it every selection purely to demo the LLM speed.
    if (selectedProspect) {
       intentMutation.mutate(selectedProspect);
       dmDraftMutation.mutate(selectedProspect);
    }
  }, [selectedProspectId]);

  if (isLoading) {
    return <div className="p-8"><p>Loading Inbox...</p></div>;
  }

  return (
    <div className="flex h-[calc(100vh-2rem)] border rounded-xl overflow-hidden bg-background">
      
      {/* Left Pane: Lead Queue */}
      <div className="w-1/3 border-r bg-muted/20 flex flex-col">
        <div className="p-4 border-b bg-background">
          <h2 className="font-semibold flex items-center gap-2">
            <Zap className="h-4 w-4 text-yellow-500 fill-yellow-500" />
            Intent Inbox
            <Badge variant="secondary" className="ml-auto">{prospects.length} Signals</Badge>
          </h2>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {prospects.map((prospect: any) => (
            <Card 
              key={prospect.id} 
              className={`cursor-pointer transition-all hover:bg-muted/50 ${selectedProspectId === prospect.id ? 'ring-2 ring-primary border-primary bg-primary/5' : ''}`}
              onClick={() => setSelectedProspectId(prospect.id)}
            >
              <CardContent className="p-3">
                <div className="flex justify-between items-start mb-1">
                  <span className="font-semibold text-sm">{prospect.name}</span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDistanceToNow(new Date(prospect.created_at))} ago
                  </span>
                </div>
                <div className="text-xs text-muted-foreground line-clamp-1 mb-2">
                  {prospect.headline}
                </div>
                <div className="bg-muted p-2 rounded-md border text-xs italic line-clamp-2">
                  "{prospect.buying_signal}"
                </div>
              </CardContent>
            </Card>
          ))}
          {prospects.length === 0 && (
            <div className="p-8 text-center text-muted-foreground text-sm flex flex-col items-center">
              <span className="animate-pulse">Waiting for AI Intent Seeder to detect signals...</span>
            </div>
          )}
        </div>
      </div>

      {/* Right Pane: AI Copilot Workspace */}
      <div className="w-2/3 flex flex-col h-full bg-background relative">
        {!selectedProspect ? (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <Target className="w-12 h-12 mb-4 opacity-20" />
            <p>Select a buying signal from the queue to run Intent Classification.</p>
          </div>
        ) : (
          <>
            {/* Prospect Header */}
            <div className="p-6 border-b flex items-start gap-4 bg-muted/10">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                <UserCircle className="w-8 h-8 text-primary" />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-bold">{selectedProspect.name}</h2>
                <div className="text-sm text-foreground flex items-center gap-2 mt-1">
                  <Building2 className="w-4 h-4 text-muted-foreground" /> {selectedProspect.company}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  {selectedProspect.headline}
                </div>
              </div>

              {/* Live Scorer Box */}
              <div className="bg-background border rounded-lg p-3 w-48 text-right shadow-sm">
                <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider font-semibold">AI Intent Score</div>
                {intentMutation.isPending ? (
                   <div className="animate-pulse h-8 w-16 bg-muted ml-auto rounded"></div>
                ) : (
                  <div className="flex flex-col items-end">
                    <span className={`text-2xl font-black ${
                      (intentMutation.data?.intent_score || 0) > 75 ? 'text-green-500' : 
                      (intentMutation.data?.intent_score || 0) > 40 ? 'text-yellow-500' : 'text-slate-500'
                    }`}>
                      {intentMutation.data?.intent_score || "?"}/100
                    </span>
                    <span className="text-[10px] text-muted-foreground leading-tight mt-1 truncate w-48 text-right opacity-80" title={intentMutation.data?.rationale}>
                      {intentMutation.data?.rationale}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              
              {/* Interaction Context */}
              <div>
                <h3 className="text-sm font-semibold flex items-center gap-2 mb-3 text-muted-foreground uppercase tracking-wider">
                  <MessageSquare className="w-4 h-4" /> Detected Signal
                </h3>
                <div className="p-4 bg-blue-500/5 border border-blue-500/20 rounded-xl text-blue-900 dark:text-blue-100 text-sm italic">
                  "{selectedProspect.buying_signal}"
                </div>
              </div>

              {/* DM Copilot */}
              <div>
                <h3 className="text-sm font-semibold flex items-center gap-2 mb-3 text-muted-foreground uppercase tracking-wider">
                  <Zap className="w-4 h-4" /> DM Copilot Drafts
                </h3>
                
                {dmDraftMutation.isPending ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="h-24 bg-muted animate-pulse rounded-xl w-full"></div>
                    ))}
                  </div>
                ) : dmDraftMutation.data ? (
                  <div className="space-y-4">
                    
                    {/* Draft 1: Direct Pitch */}
                    <div className="border rounded-xl p-4 bg-background shadow-sm hover:border-primary transition-colors group">
                      <div className="flex justify-between items-center mb-2">
                        <Badge variant="outline" className="bg-primary/5 text-primary">Direct Pitch</Badge>
                        <Button 
                          size="sm" 
                          className="h-7 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={() => updateStatusMutation.mutate({ id: selectedProspect.id, status: 'contacted' })}
                        >
                          <Send className="w-3 h-3 mr-2" /> Send via API
                        </Button>
                      </div>
                      <p className="text-sm text-foreground">{dmDraftMutation.data.draft_1}</p>
                    </div>

                    {/* Draft 2: Relationship */}
                    <div className="border rounded-xl p-4 bg-background shadow-sm hover:border-primary transition-colors group">
                      <div className="flex justify-between items-center mb-2">
                         <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20">Relationship Focus</Badge>
                         <Button size="sm" variant="secondary" className="h-7 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Send className="w-3 h-3 mr-2" /> Send via API
                        </Button>
                      </div>
                      <p className="text-sm text-foreground">{dmDraftMutation.data.draft_2}</p>
                    </div>

                    {/* Draft 3: Casual */}
                    <div className="border rounded-xl p-4 bg-background shadow-sm hover:border-primary transition-colors group">
                      <div className="flex justify-between items-center mb-2">
                         <Badge variant="outline" className="bg-purple-500/10 text-purple-600 border-purple-500/20">Short & Casual</Badge>
                         <Button size="sm" variant="secondary" className="h-7 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Send className="w-3 h-3 mr-2" /> Send via API
                        </Button>
                      </div>
                      <p className="text-sm text-foreground">{dmDraftMutation.data.draft_3}</p>
                    </div>

                  </div>
                ) : (
                  <div className="p-8 border rounded-xl text-center text-muted-foreground flex flex-col items-center">
                    <p>Failed to load drafts. Check AI Engine.</p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

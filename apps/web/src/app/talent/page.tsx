"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { 
  Briefcase, 
  MapPin, 
  Search, 
  Sparkles,
  UserCircle2,
  Zap
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

async function fetchCandidates() {
  const token = localStorage.getItem("access_token");
  const res = await fetch("http://192.168.31.242:8000/api/v1/talent/candidates", {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to fetch candidates");
  const json = await res.json();
  return json.data;
}

export default function TalentDiscoveryPage() {
  const { data: candidates = [], isLoading } = useQuery({
    queryKey: ["talent", "candidates"],
    queryFn: fetchCandidates,
    refetchInterval: 5000 // Poll for passive candidate ingestion
  });

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Talent Discovery</h2>
          <p className="text-muted-foreground">AI-driven outbound candidate sourcing mapped against open Requisitions.</p>
        </div>
        <div className="flex space-x-2">
           <Button variant="outline"><Search className="mr-2 h-4 w-4" /> Filter Skills</Button>
           <Button className="bg-emerald-600 hover:bg-emerald-700">
             <Zap className="mr-2 h-4 w-4" /> Sync Integration
           </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1,2,3,4,5,6].map(i => (
             <div key={i} className="h-48 rounded-xl bg-muted animate-pulse"></div>
          ))}
        </div>
      ) : candidates.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-24 text-center border rounded-xl border-dashed">
            <UserCircle2 className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
            <h3 className="text-lg font-semibold">No Talent Discovered Yet</h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-2">
              The AI Seeder is currently sweeping designated networks to find candidates matching your active requisitions. Check back shortly.
            </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {candidates.map((candidate: any) => (
             <Card key={candidate.id} className="group hover:border-primary/50 transition-colors cursor-pointer">
                <CardHeader className="pb-3 border-b bg-muted/20">
                    <div className="flex justify-between items-start">
                        <div>
                           <CardTitle className="text-xl flex items-center gap-2">
                               {candidate.name}
                           </CardTitle>
                           <CardDescription className="line-clamp-1 mt-1 font-medium text-foreground/80">
                               {candidate.headline}
                           </CardDescription>
                        </div>
                        {candidate.match_score > 0 && (
                            <Badge className={`px-2 py-1 ${
                                candidate.match_score > 85 ? 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20 hover:bg-emerald-500/20' : 
                                candidate.match_score > 60 ? 'bg-blue-500/10 text-blue-700 border-blue-500/20 hover:bg-blue-500/20' : 
                                'bg-yellow-500/10 text-yellow-700 border-yellow-500/20 hover:bg-yellow-500/20'
                            }`}>
                                <Sparkles className="w-3 h-3 mr-1" /> {candidate.match_score} Fit
                            </Badge>
                        )}
                    </div>
                </CardHeader>
                <CardContent className="pt-4 space-y-4">
                    <div className="flex justify-between text-sm text-muted-foreground">
                        <span className="flex items-center gap-1.5"><Briefcase className="w-4 h-4" /> {candidate.current_company || "Stealth"}</span>
                        <span className="flex items-center gap-1.5"><MapPin className="w-4 h-4" /> Remote</span>
                    </div>
                    
                    <div>
                        <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Core Skills</div>
                        <div className="flex flex-wrap gap-1.5">
                            {(() => {
                                try {
                                    const parsedSkills = JSON.parse(candidate.skills);
                                    return parsedSkills.slice(0, 5).map((skill: string, idx: number) => (
                                       <Badge key={idx} variant="secondary" className="font-normal text-xs">{skill}</Badge>
                                    ));
                                } catch (e) {
                                    return <span className="text-sm text-muted-foreground">{candidate.skills}</span>;
                                }
                            })()}
                        </div>
                    </div>

                    <div className="flex justify-between items-center pt-2 mt-2 border-t text-xs text-muted-foreground">
                        <span>Sourced {formatDistanceToNow(new Date(candidate.created_at))} ago</span>
                        <Button size="sm" variant="ghost" className="h-8">Move to ATS</Button>
                    </div>
                </CardContent>
             </Card>
          ))}
        </div>
      )}
    </div>
  );
}

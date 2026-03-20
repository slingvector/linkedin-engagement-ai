"use client";

import React, { useState, useEffect } from "react";
import { format } from "date-fns";
import { 
  ShieldCheck, 
  Activity,
  Zap,
  BotOff,
  Search,
  BookOpenCheck,
  History,
  AlertTriangle
} from "lucide-react";
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  BarChart, Bar, Cell, Legend
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function LLMOpsDashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchMetrics = async () => {
    try {
      const response = await fetch("http://192.168.31.242:8000/api/v1/llmops/metrics", {
        headers: { "Authorization": `Bearer ${localStorage.getItem('access_token')}` }
      });
      const data = await response.json();
      if (data.status === "success") {
        setMetrics(data.data);
      }
    } catch (err) {
      console.error("Failed to fetch LLMOps metrics", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading || !metrics) {
    return (
      <div className="flex-1 flex justify-center items-center h-full text-muted-foreground animate-pulse">
        <Activity className="w-6 h-6 mr-2" /> Initializing LLM-as-a-Judge Telemetry...
      </div>
    );
  }

  // Formatting chart metrics mapping moving safety over historical inferences
  const chartData = [...metrics.recent_evaluations].reverse().map((ev: any, idx: number) => ({
    name: `Exec-${metrics.recent_evaluations.length - idx}`,
    hallucination: ev.hallucination_score,
    safety: ev.safety_score,
    tone: ev.tone_score,
    similarity: (ev.distance * 100).toFixed(0)
  }));

  return (
    <div className="flex-1 space-y-6 p-8 pt-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">LLMOps Safety Plane</h2>
          <p className="text-muted-foreground">Tracking production hallucination rates, safety bounds, and Shadow Mode edit-distance logs.</p>
        </div>
        <div className="flex items-center bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full text-xs font-semibold border border-emerald-200">
          <span className="relative flex h-2 w-2 mr-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          LLM-as-a-Judge Active
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {/* Global Stats */}
        <Card className="bg-slate-50/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 flex items-center justify-between">
              Avg Human Edit Similarity <History className="w-4 h-4 text-slate-400" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-700">
               {(metrics.global_human_acceptance_rate * 100).toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">Delta between AI Draft vs Final Edit.</p>
          </CardContent>
        </Card>

        <Card className="bg-emerald-50/50 border-emerald-100">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-emerald-700 flex items-center justify-between">
              Global Platform Safety <ShieldCheck className="w-4 h-4 text-emerald-500" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-700">
               99.8%
            </div>
            <p className="text-xs text-emerald-600/80 mt-1">LLM compliance check thresholds passed.</p>
          </CardContent>
        </Card>

        <Card className="bg-amber-50/50 border-amber-100">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-amber-700 flex items-center justify-between">
              Avg Tone Alignment <BotOff className="w-4 h-4 text-amber-500" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-700">
               92.4%
            </div>
            <p className="text-xs text-amber-600/80 mt-1">Historical brand voice adherence check.</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Base */}
      <Card>
         <CardHeader>
             <CardTitle>Historical LLM-as-a-Judge Evals</CardTitle>
             <CardDescription>Automated shadow evaluations grading outputs for hallucination and safety.</CardDescription>
         </CardHeader>
         <CardContent>
             {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                        <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis yAxisId="left" domain={[60, 100]} stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis yAxisId="right" orientation="right" domain={[0, 100]} stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                        <RechartsTooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                        <Legend verticalAlign="top" height={36}/>
                        <Line yAxisId="left" type="monotone" name="Hallucination Grade (Higher=Safer)" dataKey="hallucination" stroke="#10b981" strokeWidth={3} activeDot={{ r: 8 }} />
                        <Line yAxisId="left" type="monotone" name="Tone Adherence" dataKey="tone" stroke="#f59e0b" strokeWidth={2} />
                        <Line yAxisId="right" type="monotone" name="Draft Similarity %" dataKey="similarity" stroke="#3b82f6" strokeWidth={2} strokeDasharray="5 5" />
                    </LineChart>
                </ResponsiveContainer>
             ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground bg-muted/20 rounded-lg border border-dashed">
                   Awaiting initial telemetry exhaust points...
                </div>
             )}
         </CardContent>
      </Card>

      {/* Shadow Logs Trace Explorer */}
      <h3 className="text-lg font-semibold mt-8 mb-4">Shadow Action Log (DPO Raw Sinks)</h3>
      <div className="space-y-4">
         {metrics.recent_evaluations.map((ev: any, idx: number) => (
             <Card key={idx} className="border border-muted shadow-sm hover:shadow-md transition-shadow">
                <CardHeader className="bg-muted/30 py-3 flex flex-row items-center justify-between border-b">
                   <div className="flex items-center gap-3">
                       <Badge variant="outline" className="bg-background">ID: {ev.log_id.slice(0, 8)}</Badge>
                       <span className="text-sm font-semibold uppercase text-muted-foreground flex items-center gap-2">
                           <Zap className="w-3 h-3" /> {ev.action.replace("_", " ")}
                       </span>
                   </div>
                   <div className="flex items-center gap-3 text-sm">
                       <span className="text-muted-foreground">Similarity:</span>
                       <span className={`font-mono font-bold ${ev.distance > 0.8 ? 'text-emerald-600' : ev.distance > 0.4 ? 'text-amber-600' : 'text-rose-600'}`}>
                           {(ev.distance * 100).toFixed(0)}%
                       </span>
                   </div>
                </CardHeader>
                <CardContent className="p-0">
                   <div className="grid grid-cols-2 divide-x">
                       <div className="p-4 bg-amber-50/20">
                          <h4 className="text-xs font-semibold uppercase text-amber-600/60 tracking-wider mb-2 flex items-center gap-2">
                              <BotOff className="w-3 h-3" /> AI Raw Draft (Perceived)
                          </h4>
                          <div className="text-sm text-foreground/80 font-mono">
                              "{ev.ai_draft}"
                          </div>
                       </div>
                       <div className="p-4 bg-emerald-50/20">
                           <h4 className="text-xs font-semibold uppercase text-emerald-600/60 tracking-wider mb-2 flex items-center gap-2">
                              <BookOpenCheck className="w-3 h-3" /> Human Final Edit (Truth)
                          </h4>
                          <div className="text-sm text-foreground/80 font-mono">
                              "{ev.human_edit}"
                          </div>
                       </div>
                   </div>
                   <div className="px-4 py-3 bg-slate-50 border-t flex items-start gap-3">
                       <AlertTriangle className="w-4 h-4 text-slate-400 mt-0.5" />
                       <div>
                           <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Judge Rationale</div>
                           <div className="text-sm text-slate-600">{ev.rationale}</div>
                       </div>
                   </div>
                </CardContent>
             </Card>
         ))}
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { format } from "date-fns";
import { 
  Building2, 
  Send,
  Mail,
  Zap,
  Bot,
  CheckCircle2,
  Clock,
  ArrowRight
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

// Mocking the Campaign state for the UI development
const MOCK_CAMPAIGNS = [
  {
    id: "camp-1",
    name: "CXO Series A Outbound",
    status: "drafting",
    account: { company_name: "Acme Corp", industry: "B2B SaaS" },
    signals: ["funding_round"],
    steps: []
  }
];

export default function CampaignsPage() {
  const [activeCampaign, setActiveCampaign] = useState<any>(MOCK_CAMPAIGNS[0]);
  const [isGenerating, setIsGenerating] = useState(false);

  const generateSequence = async () => {
    setIsGenerating(true);
    // Simulate AI generation delay
    setTimeout(() => {
      setActiveCampaign({
        ...activeCampaign,
        status: "ready",
        steps: [
          {
            step_order: 1,
            subject: "Scaling engineering post-Series A",
            body: "Hi [Name],\n\nNoticed Acme Corp just closed a $50M Series B—huge congrats. I imagine scaling the engineering team quickly while maintaining code quality is top of mind right now.\n\nWe provide a platform that automates technical initial screens, saving engineering leaders 15+ hours a week. Open to seeing a 2-minute interactive demo?\n\nBest,\n[Your Name]"
          },
          {
            step_order: 2,
            subject: "Re: Scaling engineering post-Series A",
            body: "Hi [Name],\n\nBumping this to the top of your inbox. Since you're actively hiring, I thought you might find this case study helpful: how [Competitor] reduced their time-to-hire by 40% using our platform.\n\nLet me know if you're open to a brief chat.\n\nBest,\n[Your Name]"
          },
          {
            step_order: 3,
            subject: "Closing the loop here",
            body: "Hi [Name],\n\nI haven't heard back, so I'll assume timing isn't right to discuss engineering hiring efficiency at Acme Corp.\n\nI'll pause my outreach. If things change as you execute on the Series B roadmap, feel free to reach out.\n\nBest,\n[Your Name]"
          }
        ]
      });
      setIsGenerating(false);
    }, 2000);
  };

  const deployCampaign = () => {
     setActiveCampaign({...activeCampaign, status: "active"});
  };

  return (
    <div className="flex-1 space-y-6 p-8 pt-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Campaign Orchestrator</h2>
          <p className="text-muted-foreground">Manage multi-touch generative outbound sequences tied to Account Signals.</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-4 lg:grid-cols-5">
        
        {/* Left Sidebar - Active Campaigns */}
        <div className="col-span-1 border rounded-xl bg-muted/20 p-4 space-y-4">
           <h3 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground mb-4">Active Campaigns</h3>
           {MOCK_CAMPAIGNS.map(camp => (
              <div 
                key={camp.id} 
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${activeCampaign.id === camp.id ? 'bg-primary/5 border-primary shadow-sm' : 'bg-background hover:bg-muted/50'}`}
                onClick={() => setActiveCampaign(camp)}
              >
                  <div className="font-semibold text-sm mb-1 line-clamp-1">{camp.name}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Building2 className="w-3 h-3" /> {camp.account.company_name}
                  </div>
              </div>
           ))}
        </div>

        {/* Main Workspace */}
        <div className="col-span-3 lg:col-span-4 space-y-6">
           <Card className="border-indigo-100 shadow-sm">
             <CardHeader className="bg-indigo-50/50 pb-4 border-b">
                <div className="flex justify-between items-start">
                    <div>
                        <Badge className="mb-2 bg-indigo-100 hover:bg-indigo-200 text-indigo-700">{activeCampaign.status}</Badge>
                        <CardTitle className="text-2xl font-bold">{activeCampaign.name}</CardTitle>
                        <CardDescription className="mt-1 flex items-center gap-2">
                           Targeting <strong className="text-foreground">{activeCampaign.account.company_name}</strong> based on signal <strong>{activeCampaign.signals[0].replace("_", " ")}</strong>
                        </CardDescription>
                    </div>
                    {activeCampaign.steps.length === 0 ? (
                        <Button onClick={generateSequence} disabled={isGenerating} size="lg" className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 shadow-md">
                            <Bot className={`w-4 h-4 mr-2 ${isGenerating ? 'animate-pulse' : ''}`} /> 
                            {isGenerating ? 'Generating Sequence...' : 'Auto-Generate Sequence'}
                        </Button>
                    ) : activeCampaign.status === "active" ? (
                        <Button disabled variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700">
                           <CheckCircle2 className="w-4 h-4 mr-2" /> Sequence Active
                        </Button>
                    ) : (
                        <Button onClick={deployCampaign} size="lg" className="bg-emerald-600 hover:bg-emerald-700 shadow-md">
                            <Send className="w-4 h-4 mr-2" /> Deploy via SendGrid Mock
                        </Button>
                    )}
                </div>
             </CardHeader>
             
             {activeCampaign.steps.length > 0 && (
                 <CardContent className="pt-6 space-y-8">
                    {activeCampaign.steps.map((step: any, idx: number) => (
                        <div key={idx} className="relative pl-6 border-l-2 border-muted space-y-3">
                            <div className="absolute w-6 h-6 rounded-full bg-background border-2 border-indigo-200 flex items-center justify-center -left-[13px] top-0 text-xs font-bold text-indigo-700">
                                {step.step_order}
                            </div>
                            
                            <div className="flex justify-between items-center ml-2">
                                <h4 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                                   <Mail className="w-4 h-4" /> 
                                   {idx === 0 ? "Initial Touch" : idx === 1 ? "Follow Up (Day 3)" : "Breakup (Day 7)"}
                                </h4>
                                <Badge variant="outline" className="text-[10px] bg-background">
                                   {activeCampaign.status === "active" ? (idx === 0 ? "Sent" : "Queued") : "Draft"}
                                </Badge>
                            </div>

                            <div className="bg-muted/30 rounded-lg p-4 ml-2 border space-y-3">
                                <div className="flex items-center gap-2 text-sm border-b pb-2">
                                    <span className="text-muted-foreground font-medium w-16">Subject:</span>
                                    <span className="font-semibold">{step.subject}</span>
                                </div>
                                <Textarea 
                                   defaultValue={step.body}
                                   className="min-h-[120px] font-mono text-xs bg-background resize-none border-none shadow-none focus-visible:ring-0"
                                />
                            </div>
                        </div>
                    ))}
                 </CardContent>
             )}
             
             {activeCampaign.steps.length === 0 && !isGenerating && (
                 <div className="p-12 text-center flex flex-col items-center">
                     <div className="w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center mb-4">
                        <Zap className="w-8 h-8 text-indigo-500" />
                     </div>
                     <h3 className="text-lg font-semibold space-y-1">AI Sequence Pending</h3>
                     <p className="text-sm text-muted-foreground max-w-md mt-2">
                        Click "Auto-Generate" to unleash the AI Engine. It will map the {activeCampaign.signals[0].replace("_", " ")} trigger against your Value Prop to craft a highly converting 3-touch cadence.
                     </p>
                 </div>
             )}
           </Card>
        </div>

      </div>
    </div>
  );
}

"use client"

import { useState } from "react"
import { Building, MapPin, ExternalLink, Calendar, ChevronRight } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

type ApplicationStatus = "saved" | "applied" | "interviewing" | "rejected"

interface Application {
  id: string
  job_title: string
  company: string
  location: string
  match_score: number
  status: ApplicationStatus
  applied_at?: string
}

const initialMockData: Application[] = [
  { id: "1", job_title: "Frontend Developer", company: "Vercel", location: "New York, NY", match_score: 95, status: "saved" },
  { id: "2", job_title: "Backend Software Engineer", company: "Stripe", location: "Remote", match_score: 88, status: "applied", applied_at: "2024-03-18" },
  { id: "3", job_title: "Prompt Engineer", company: "Anthropic", location: "San Francisco, CA", match_score: 92, status: "interviewing", applied_at: "2024-03-10" },
  { id: "4", job_title: "Data Engineer", company: "Snowflake", location: "Remote", match_score: 75, status: "rejected", applied_at: "2024-02-28" },
]

const COLUMNS: { id: ApplicationStatus; label: string; color: string }[] = [
  { id: "saved", label: "Saved for Later", color: "bg-slate-500/10 text-slate-500 border-slate-500/20" },
  { id: "applied", label: "Applied", color: "bg-blue-500/10 text-blue-500 border-blue-500/20" },
  { id: "interviewing", label: "Interviewing", color: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" },
  { id: "rejected", label: "Rejected", color: "bg-red-500/10 text-red-500 border-red-500/20" },
]

export default function ApplicationsKanbanPage() {
  const [applications, setApplications] = useState<Application[]>(initialMockData)

  const moveApplication = async (appId: string, currentStatus: ApplicationStatus, direction: 1 | -1) => {
    const currentIdx = COLUMNS.findIndex(c => c.id === currentStatus)
    const nextIdx = currentIdx + direction
    if (nextIdx < 0 || nextIdx >= COLUMNS.length) return
    
    const nextStatus = COLUMNS[nextIdx].id
    
    // Optimistic UI Update
    setApplications(prev => prev.map(app => 
        app.id === appId ? { ...app, status: nextStatus } : app
    ))

    // In a real implementation we would PUT /api/v1/career/applications/{id}/status
    /*
    await fetch(`http://192.168.31.242:8000/api/v1/career/applications/${appId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus })
    })
    */
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6 h-[calc(100vh-4rem)] flex flex-col min-h-0 min-w-0">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Application Tracker</h2>
        <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-muted-foreground">Total Active: {applications.filter(a => a.status !== 'rejected').length}</span>
        </div>
      </div>

      <div className="flex-1 flex gap-6 overflow-x-auto pb-4 mt-6 snap-x min-h-0">
        {COLUMNS.map(col => (
          <div key={col.id} className="flex flex-col w-80 min-w-[320px] shrink-0 bg-muted/30 rounded-xl p-4 snap-center border border-muted/50">
            <div className="flex items-center justify-between mb-4 px-2">
                <Badge variant="outline" className={`font-semibold py-1 px-3 ${col.color}`}>
                    {col.label}
                </Badge>
                <Badge variant="secondary" className="rounded-full shrink-0 tabular-nums">
                    {applications.filter(a => a.status === col.id).length}
                </Badge>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
                {applications.filter(a => a.status === col.id).map(app => (
                    <Card key={app.id} className="flex flex-col hover:border-primary/40 transition-colors bg-background shadow-sm">
                        <CardHeader className="p-4 pb-2">
                            <CardTitle className="text-base line-clamp-1">{app.job_title}</CardTitle>
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-1">
                                <Building className="h-3 w-3 shrink-0" />
                                <span className="line-clamp-1 truncate">{app.company}</span>
                            </div>
                        </CardHeader>
                        
                        <CardContent className="p-4 pt-0 space-y-3">
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                <MapPin className="h-3 w-3 shrink-0" />
                                <span className="truncate">{app.location}</span>
                            </div>
                            
                            {app.applied_at && (
                                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                    <Calendar className="h-3 w-3 shrink-0" />
                                    <span>Applied {new Date(app.applied_at).toLocaleDateString()}</span>
                                </div>
                            )}
                            
                            <Badge variant="secondary" className="bg-indigo-500/10 text-indigo-500 hover:bg-indigo-500/20 w-fit">
                                {app.match_score}% Match
                            </Badge>
                        </CardContent>
                        
                        <CardFooter className="p-3 pt-0 flex justify-between border-t bg-muted/10 border-muted/50">
                            <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-8 px-2 text-xs"
                                disabled={col.id === COLUMNS[0].id}
                                onClick={() => moveApplication(app.id, app.status, -1)}
                            >
                                Back
                            </Button>
                            <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-8 px-2 text-xs"
                                disabled={col.id === COLUMNS[COLUMNS.length - 1].id}
                                onClick={() => moveApplication(app.id, app.status, 1)}
                            >
                                Next <ChevronRight className="ml-1 h-3 w-3" />
                            </Button>
                        </CardFooter>
                    </Card>
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
    Search, Briefcase, ActivitySquare, ShieldAlert, Users, CalendarDays, 
    FileText, Lightbulb, PenTool, LayoutDashboard, Rocket
} from "lucide-react";

export function GlobalSearch() {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState("");
    const router = useRouter();

    useEffect(() => {
        const down = (e: KeyboardEvent) => {
            if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                setOpen((open) => !open);
            }
        };
        document.addEventListener("keydown", down);
        return () => document.removeEventListener("keydown", down);
    }, []);

    const routes = [
        { name: "Creator Hub / Post Writer", href: "/", icon: PenTool, category: "Creator" },
        { name: "Content Analytics", href: "/analytics", icon: LayoutDashboard, category: "Creator" },
        { name: "Idea Workspace", href: "/ideas", icon: Lightbulb, category: "Creator" },
        { name: "Schedule Dashboard", href: "/schedule", icon: CalendarDays, category: "Creator" },
        { name: "Comment Copilot (Radar)", href: "/radar", icon: Search, category: "Creator" },
        { name: "Job Tracking Desk", href: "/career", icon: FileText, category: "Job Seeker" },
        { name: "Talent Discovery", href: "/talent", icon: Users, category: "HR Agent" },
        { name: "Applicant Tracking (ATS)", href: "/ats", icon: Briefcase, category: "HR Agent" },
        { name: "Enterprise ABM Radar", href: "/abm", icon: ShieldAlert, category: "Enterprise" },
        { name: "Campaign Orchestrator", href: "/campaigns", icon: Rocket, category: "Enterprise" },
        { name: "LLMOps Safety Dashboard", href: "/llmops", icon: ActivitySquare, category: "Core" },
    ];

    const filtered = routes.filter(r => r.name.toLowerCase().includes(query.toLowerCase()) || r.category.toLowerCase().includes(query.toLowerCase()));

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-start justify-center pt-[15vh]">
            <div 
                className="fixed inset-0" 
                onClick={() => setOpen(false)}
            />
            <div className="relative w-full max-w-xl bg-background border rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                <div className="flex items-center px-4 py-3 border-b">
                    <Search className="w-5 h-5 text-muted-foreground mr-3" />
                    <input 
                        className="flex-1 bg-transparent border-none outline-none text-base placeholder:text-muted-foreground" 
                        placeholder="Type a command or search modules..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        autoFocus
                    />
                    <kbd className="hidden sm:inline-block pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
                        ESC
                    </kbd>
                </div>
                
                <div className="max-h-[350px] overflow-y-auto p-2">
                    {filtered.length === 0 ? (
                        <div className="py-6 text-center text-sm text-muted-foreground">
                            No modules found.
                        </div>
                    ) : (
                        Object.entries(
                            filtered.reduce((acc, route) => {
                                acc[route.category] = acc[route.category] || [];
                                acc[route.category].push(route);
                                return acc;
                            }, {} as Record<string, typeof routes>)
                        ).map(([category, items]) => (
                            <div key={category} className="mb-4 last:mb-0">
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                    {category}
                                </div>
                                {items.map(route => {
                                    const Icon = route.icon;
                                    return (
                                        <div 
                                            key={route.href}
                                            onClick={() => {
                                                router.push(route.href);
                                                setOpen(false);
                                            }}
                                            className="flex items-center px-2 py-2 text-sm rounded-md cursor-pointer hover:bg-muted/50 hover:text-foreground text-muted-foreground transition-colors"
                                        >
                                            <Icon className="w-4 h-4 mr-3 text-slate-500" />
                                            {route.name}
                                        </div>
                                    );
                                })}
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}

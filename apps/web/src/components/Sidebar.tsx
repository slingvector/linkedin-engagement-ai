"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Home, PenTool, Radar, Lightbulb, CalendarDays, Settings, BarChart, Briefcase, LayoutDashboard, Target, Zap, Users, ShieldAlert, Rocket, ActivitySquare } from "lucide-react"

import { cn } from "@/lib/utils"

const navItems = [
  { name: "Home", href: "/", icon: Home },
  { name: "Idea Engine", href: "/ideas", icon: Lightbulb },
  { name: "Post Creator", href: "/posts", icon: PenTool },
  { name: "Content Calendar", href: "/calendar", icon: CalendarDays },
  { name: "Creator Radar", href: "/radar", icon: Radar },
  { name: "Career Agent", href: "/jobs", icon: Briefcase },
  { name: "Applications Tracking", href: "/applications", icon: LayoutDashboard },
  { name: "Lead Inbox", href: "/inbox", icon: Zap },
  { name: "Deals Pipeline", href: "/deals", icon: Target },
  { name: "Talent Discovery", href: "/talent", icon: Users },
  { name: "Applicant Pipeline (ATS)", href: "/ats", icon: Briefcase },
  { name: "Enterprise ABM Radar", href: "/abm", icon: ShieldAlert },
  { name: "Campaign Orchestrator", href: "/campaigns", icon: Rocket },
  { name: "LLMOps Safety Plane", href: "/llmops", icon: ActivitySquare },
  { name: "Settings", href: "/settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex h-screen w-64 flex-col border-r bg-muted/40 px-3 py-4">
      <div className="mb-8 px-4">
        <h2 className="text-lg font-semibold tracking-tight">
          LinkedIn Copilot
        </h2>
      </div>
      <div className="flex-1 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:text-primary",
              pathname === item.href
                ? "bg-muted text-primary"
                : "text-muted-foreground"
            )}
          >
            <item.icon className="h-4 w-4" />
            {item.name}
          </Link>
        ))}
      </div>
    </div>
  )
}

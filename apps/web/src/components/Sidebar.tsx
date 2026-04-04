"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import {
  Home, PenTool, Radar, Lightbulb, CalendarDays, Settings,
  Briefcase, LayoutDashboard, Target, Zap, Users, ShieldAlert,
  Rocket, ActivitySquare, LogOut, Linkedin,
} from "lucide-react"

import { cn } from "@/lib/utils"
import { useAuthStore } from "@/lib/store"

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
  const router = useRouter()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    router.push("/login")
  }

  // Get initials for avatar fallback
  const initials = user?.full_name
    ? user.full_name.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase()
    : "?"

  return (
    <div className="flex h-screen w-64 flex-col border-r bg-muted/40 px-3 py-4">
      {/* App name */}
      <div className="mb-8 px-4 flex items-center gap-2">
        <Linkedin className="h-5 w-5 text-[#0A66C2]" />
        <h2 className="text-lg font-semibold tracking-tight">Copilot</h2>
      </div>

      {/* Nav items */}
      <div className="flex-1 space-y-1 overflow-y-auto">
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

      {/* User profile + logout */}
      <div className="mt-4 border-t pt-4">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg">
          {/* Avatar */}
          {user?.profile_picture_url ? (
            <img
              src={user.profile_picture_url}
              alt={user.full_name}
              className="h-8 w-8 rounded-full object-cover flex-shrink-0"
            />
          ) : (
            <div className="h-8 w-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-semibold flex-shrink-0">
              {initials}
            </div>
          )}
          {/* Name + email */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.full_name ?? "Loading..."}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email ?? ""}</p>
          </div>
          {/* Logout button */}
          <button
            onClick={handleLogout}
            title="Sign out"
            className="text-muted-foreground hover:text-destructive transition-colors flex-shrink-0"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

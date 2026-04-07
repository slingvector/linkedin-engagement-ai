"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { format, parseISO } from "date-fns"
import {
  CalendarDays, Clock, CheckCircle2, TrendingUp,
  Flame, BarChart2, Info, Zap, Sparkles
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useHeatmap } from "@/hooks/useHeatmap"
import { SmartFillDrawer } from "@/components/SmartFillDrawer"

// ─── Constants ──────────────────────────────────────────────────────────────

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
const HOURS = Array.from({ length: 13 }, (_, i) => i + 7) // 7am–7pm

function heatColor(rate: number | undefined): string {
  if (rate === undefined || rate === null) return "bg-muted/20 border-transparent"
  if (rate >= 0.85) return "bg-emerald-500/80 border-emerald-400/60 shadow-sm shadow-emerald-500/20"
  if (rate >= 0.7)  return "bg-emerald-400/60 border-emerald-300/40"
  if (rate >= 0.5)  return "bg-yellow-400/50 border-yellow-300/40"
  if (rate >= 0.3)  return "bg-orange-400/40 border-orange-300/30"
  if (rate >= 0.1)  return "bg-red-400/30 border-red-300/20"
  return "bg-muted/20 border-transparent"
}

function HeatLegend() {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span>Low</span>
      {["bg-red-400/30","bg-orange-400/40","bg-yellow-400/50","bg-emerald-400/60","bg-emerald-500/80"].map((cls, i) => (
        <span key={i} className={`w-5 h-3 rounded-sm border ${cls}`} />
      ))}
      <span>High engagement</span>
    </div>
  )
}

// ─── Heatmap Grid ────────────────────────────────────────────────────────────

function HeatmapGrid({ heatmap }: { heatmap: Record<string, Record<string, number>> }) {
  const [tooltip, setTooltip] = useState<{ day: string; hour: number; rate: number } | null>(null)

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[640px]">
        {/* Hour labels row */}
        <div className="grid gap-1" style={{ gridTemplateColumns: `64px repeat(${HOURS.length}, 1fr)` }}>
          <div />
          {HOURS.map(h => (
            <div key={h} className="text-center text-[10px] text-muted-foreground font-mono pb-1">
              {h > 12 ? `${h - 12}pm` : h === 12 ? "12p" : `${h}am`}
            </div>
          ))}
        </div>

        {/* Day rows */}
        {DAYS.map((day, di) => (
          <div
            key={day}
            className="grid gap-1 mb-1"
            style={{ gridTemplateColumns: `64px repeat(${HOURS.length}, 1fr)` }}
          >
            <div className="text-xs font-medium text-muted-foreground flex items-center pr-2 justify-end">
              {DAY_LABELS[di]}
            </div>
            {HOURS.map(h => {
              const rate = heatmap[day]?.[String(h)]
              return (
                <div
                  key={h}
                  className={`h-7 rounded border cursor-pointer transition-all hover:scale-110 hover:z-10 relative ${heatColor(rate)}`}
                  onMouseEnter={() => rate !== undefined && setTooltip({ day: DAY_LABELS[di], hour: h, rate })}
                  onMouseLeave={() => setTooltip(null)}
                />
              )
            })}
          </div>
        ))}

        {/* Floating tooltip */}
        {tooltip && (
          <div className="mt-2 text-xs text-center text-muted-foreground bg-muted/60 rounded px-3 py-1.5 inline-block">
            <span className="font-semibold text-foreground">{tooltip.day} {tooltip.hour > 12 ? `${tooltip.hour - 12}pm` : `${tooltip.hour}am`}</span>
            {" "}— {(tooltip.rate * 100).toFixed(0)}% relative engagement score
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Best Slots Panel ────────────────────────────────────────────────────────

function BestSlotsPanel({ slots, dataSource }: {
  slots: Array<{ day: string; hour: number; avg_engagement_rate: number }>
  dataSource: "personal" | "global_benchmark"
}) {
  return (
    <div className="space-y-2">
      {dataSource === "global_benchmark" && (
        <div className="flex items-start gap-2 text-xs text-muted-foreground bg-blue-500/10 border border-blue-500/20 rounded p-2.5">
          <Info className="h-3.5 w-3.5 mt-0.5 shrink-0 text-blue-400" />
          <span>Using LinkedIn global benchmarks. Post more to unlock your personal timing data.</span>
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {slots.slice(0, 6).map((s, i) => {
          const label = s.hour > 12 ? `${s.hour - 12}:00 PM` : `${s.hour}:00 AM`
          const dayLabel = s.day.charAt(0).toUpperCase() + s.day.slice(1)
          return (
            <div
              key={i}
              className="flex items-center gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2.5"
            >
              <div className="flex flex-col items-center justify-center w-8 h-8 bg-emerald-500/15 rounded-md">
                <Flame className={`h-4 w-4 ${i === 0 ? "text-emerald-400" : "text-emerald-600"}`} />
              </div>
              <div>
                <div className="text-sm font-semibold">{dayLabel}</div>
                <div className="text-xs text-muted-foreground">{label}</div>
              </div>
              <div className="ml-auto text-sm font-bold text-emerald-400">
                {(s.avg_engagement_rate * 100).toFixed(0)}%
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Post List ───────────────────────────────────────────────────────────────

function PostList({ posts }: { posts: any[] }) {
  if (posts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-24 border-2 border-dashed rounded-lg text-muted-foreground">
        <CalendarDays className="h-12 w-12 mb-4 opacity-20" />
        <p>No scheduled posts yet. Head to the Post Creator to draft and schedule content!</p>
      </div>
    )
  }
  return (
    <div className="space-y-4 max-w-4xl">
      {posts.map((post: any) => (
        <Card key={post.id} className="relative overflow-hidden border-muted">
          <div className={`absolute top-0 left-0 w-1.5 h-full ${post.status === 'published' ? 'bg-emerald-500' : 'bg-blue-500'}`} />
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row justify-between gap-4">
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant={post.status === 'published' ? 'default' : 'secondary'}
                    className={post.status === 'published' ? 'bg-emerald-600 text-white' : ''}>
                    {post.status.toUpperCase()}
                  </Badge>
                  <span className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    {post.status === 'published'
                      ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      : <Clock className="h-3.5 w-3.5" />}
                    {post.scheduled_at ? format(parseISO(post.scheduled_at), "PPP 'at' p") : "Not scheduled"}
                  </span>
                </div>
                <h3 className="font-semibold text-lg line-clamp-1">{post.topic}</h3>
                <p className="text-sm text-muted-foreground line-clamp-2">{post.hook}</p>
              </div>
              {post.status === 'published' && (
                <div className="flex flex-col items-end justify-center gap-1 text-xs text-muted-foreground border-l pl-4 md:min-w-[140px]">
                  <div className="flex items-center gap-1"><TrendingUp className="h-3 w-3" /> {post.impressions ?? 0} impressions</div>
                  <div className="flex items-center gap-1"><Zap className="h-3 w-3 text-yellow-400" /> {post.likes ?? 0} likes · {post.comments_count ?? 0} comments</div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function CalendarPage() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [newDrafts, setNewDrafts] = useState<any[]>([])

  const { data: heatmapData, isLoading: heatmapLoading } = useHeatmap()

  const { data: posts, isLoading: postsLoading } = useQuery({
    queryKey: ["posts-calendar"],
    queryFn: async () => {
      const res = await api.get("/posts?per_page=50")
      return res.data.posts || []
    }
  })

  const scheduledPosts = posts
    ?.filter((p: any) => p.status === "scheduled" || p.status === "published")
    .sort((a: any, b: any) => {
      const dateA = a.scheduled_at ? new Date(a.scheduled_at).getTime() : 0
      const dateB = b.scheduled_at ? new Date(b.scheduled_at).getTime() : 0
      return dateB - dateA
    }) ?? []

  return (
    <div className="flex flex-col h-full p-6 space-y-6">
      {/* Smart Fill Drawer */}
      <SmartFillDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onPostsCreated={(posts) => setNewDrafts(posts)}
      />

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight inline-flex items-center gap-2">
            <CalendarDays className="h-8 w-8 text-blue-500" />
            Content Calendar
          </h1>
          <p className="text-muted-foreground mt-1.5">
            Plan, schedule and optimise your LinkedIn content strategy.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {heatmapData && (
            <Badge variant="outline" className="text-xs text-muted-foreground gap-1.5 py-1 px-2.5">
              <BarChart2 className="h-3.5 w-3.5" />
              {heatmapData.data_source === "personal"
                ? `Personal heatmap · ${heatmapData.sample_size} posts`
                : "Global LinkedIn benchmarks"}
            </Badge>
          )}
          <Button
            onClick={() => setDrawerOpen(true)}
            className="gap-2 bg-purple-600 hover:bg-purple-500 text-white"
          >
            <Sparkles className="h-4 w-4" />
            AI Fill My Week
          </Button>
        </div>
      </div>

      {/* New drafts preview (shown after Smart Fill runs) */}
      {newDrafts.length > 0 && (
        <div className="border border-emerald-500/20 bg-emerald-500/5 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-emerald-400 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              {newDrafts.length} draft posts created and scheduled!
            </p>
            <button
              className="text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setNewDrafts([])}
            >
              Dismiss
            </button>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {newDrafts.slice(0, 4).map((draft: any) => (
              <div
                key={draft.id}
                className="bg-background border border-border rounded p-3 text-xs space-y-1"
              >
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Zap className="h-3 w-3 text-emerald-400" />
                  {draft.scheduled_at
                    ? format(new Date(draft.scheduled_at), "EEE, MMM d 'at' h:mm a")
                    : "Draft"}
                </div>
                <p className="font-medium line-clamp-1">{draft.hook}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="heatmap" className="flex-1">
        <TabsList>
          <TabsTrigger value="heatmap" className="gap-2">
            <Flame className="h-4 w-4" /> Best Times to Post
          </TabsTrigger>
          <TabsTrigger value="schedule" className="gap-2">
            <CalendarDays className="h-4 w-4" /> Scheduled Posts
          </TabsTrigger>
        </TabsList>

        {/* ── Heatmap Tab ── */}
        <TabsContent value="heatmap" className="space-y-6 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Weekly Engagement Heatmap</CardTitle>
              <CardDescription>
                Hover over any slot to see its relative engagement score. Green = high reach, Red = low reach.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {heatmapLoading ? (
                <div className="h-48 flex items-center justify-center text-muted-foreground animate-pulse">
                  Calculating your best posting windows...
                </div>
              ) : heatmapData ? (
                <>
                  <HeatmapGrid heatmap={heatmapData.heatmap} />
                  <HeatLegend />
                </>
              ) : null}
            </CardContent>
          </Card>

          {heatmapData && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Flame className="h-4 w-4 text-emerald-400" />
                  Top Posting Windows
                </CardTitle>
                <CardDescription>
                  Schedule your most important posts during these windows for maximum reach.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <BestSlotsPanel
                  slots={heatmapData.best_slots}
                  dataSource={heatmapData.data_source}
                />
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ── Schedule Tab ── */}
        <TabsContent value="schedule" className="mt-4">
          {postsLoading ? (
            <div className="text-center p-12 text-muted-foreground animate-pulse">Loading calendar...</div>
          ) : (
            <PostList posts={scheduledPosts} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

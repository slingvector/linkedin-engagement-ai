"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api, apiV2 } from "@/lib/api"
import { format, parseISO } from "date-fns"
import {
  Sparkles, X, Plus, Minus, Loader2, FileText,
  Layout, Video, CheckCircle2, ChevronRight, Zap
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

// ── Types ─────────────────────────────────────────────────────────────────────

type GeneratedPost = {
  id: string
  hook: string
  body_content: string
  call_to_action: string
  topic: string
  status: string
  scheduled_at: string | null
  generation_metadata?: {
    pillar?: string
    format?: string
    heatmap_slot?: { day: string; hour: number }
  }
}

type SmartFillResponse = {
  posts: GeneratedPost[]
  message: string
}

const FORMAT_ICONS: Record<string, React.ReactNode> = {
  text: <FileText className="h-3.5 w-3.5" />,
  carousel: <Layout className="h-3.5 w-3.5" />,
  video: <Video className="h-3.5 w-3.5" />,
}

const FORMAT_COLORS: Record<string, string> = {
  text: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  carousel: "bg-purple-500/15 text-purple-400 border-purple-500/20",
  video: "bg-orange-500/15 text-orange-400 border-orange-500/20",
}

// ── Draft Post Card ───────────────────────────────────────────────────────────

function DraftPostCard({ post }: { post: GeneratedPost }) {
  const format_type = post.generation_metadata?.format || "text"
  const pillar = post.generation_metadata?.pillar
  const slot = post.generation_metadata?.heatmap_slot

  const scheduleLabel = post.scheduled_at
    ? format(parseISO(post.scheduled_at), "EEE, MMM d 'at' h:mm a")
    : slot
    ? `${slot.day.slice(0,3).toUpperCase()} ${slot.hour > 12 ? slot.hour - 12 + "pm" : slot.hour + "am"}`
    : "Not scheduled"

  return (
    <Card className="border-muted/60 bg-background/60 hover:border-muted transition-colors">
      <CardContent className="p-4 space-y-2">
        {/* Header row */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium ${FORMAT_COLORS[format_type] || FORMAT_COLORS.text}`}>
            {FORMAT_ICONS[format_type]}
            {format_type}
          </span>
          {pillar && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0.5 text-muted-foreground">
              {pillar}
            </Badge>
          )}
          <span className="ml-auto text-[10px] text-muted-foreground flex items-center gap-1">
            <Zap className="h-3 w-3 text-emerald-400" />
            {scheduleLabel}
          </span>
        </div>

        {/* Hook */}
        <p className="text-sm font-semibold line-clamp-2 leading-snug">{post.hook}</p>

        {/* Body preview */}
        <p className="text-xs text-muted-foreground line-clamp-2">{post.body_content}</p>
      </CardContent>
    </Card>
  )
}

// ── Main Drawer ───────────────────────────────────────────────────────────────

type Props = {
  open: boolean
  onClose: () => void
  onPostsCreated: (posts: GeneratedPost[]) => void
}

const DEFAULT_PILLARS = ["", "", ""]
const FORMATS = ["text", "carousel", "video"]

export function SmartFillDrawer({ open, onClose, onPostsCreated }: Props) {
  const queryClient = useQueryClient()

  const [pillars, setPillars] = useState<string[]>(["", "", ""])
  const [postsPerWeek, setPostsPerWeek] = useState(4)
  const [selectedFormats, setSelectedFormats] = useState<string[]>(["text", "carousel"])
  const [result, setResult] = useState<SmartFillResponse | null>(null)

  const mutation = useMutation({
    mutationFn: async () => {
      const validPillars = pillars.filter(p => p.trim().length > 0)
      if (validPillars.length === 0) throw new Error("Add at least one content pillar")
      const res = await apiV2.post("/calendar/smart-fill", {
        pillars: validPillars,
        posts_per_week: postsPerWeek,
        preferred_formats: selectedFormats,
      })
      return res.data as SmartFillResponse
    },
    onSuccess: (data) => {
      setResult(data)
      queryClient.invalidateQueries({ queryKey: ["posts-calendar"] })
      onPostsCreated(data.posts)
    },
  })

  const toggleFormat = (f: string) => {
    setSelectedFormats(prev =>
      prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]
    )
  }

  const handlePillarChange = (i: number, val: string) => {
    const next = [...pillars]
    next[i] = val
    setPillars(next)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer panel */}
      <div className="relative w-full max-w-md h-full bg-background border-l border-border flex flex-col shadow-2xl animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-purple-400" />
              AI Fill My Week
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Generate a full week of draft posts, timed by your engagement data.
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {!result ? (
            <>
              {/* Content Pillars */}
              <div className="space-y-2">
                <label className="text-sm font-semibold">Content Pillars</label>
                <p className="text-xs text-muted-foreground">Topics you want to rotate across the week</p>
                <div className="space-y-2">
                  {pillars.map((p, i) => (
                    <Input
                      key={i}
                      placeholder={`Pillar ${i + 1} (e.g. AI Automation)`}
                      value={p}
                      onChange={e => handlePillarChange(i, e.target.value)}
                      className="text-sm"
                    />
                  ))}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs text-muted-foreground gap-1"
                  onClick={() => pillars.length < 5 && setPillars([...pillars, ""])}
                >
                  <Plus className="h-3 w-3" /> Add pillar
                </Button>
              </div>

              {/* Posts per week */}
              <div className="space-y-2">
                <label className="text-sm font-semibold">Posts Per Week</label>
                <div className="flex items-center gap-3">
                  <Button
                    variant="outline" size="icon"
                    onClick={() => setPostsPerWeek(Math.max(1, postsPerWeek - 1))}
                  >
                    <Minus className="h-3.5 w-3.5" />
                  </Button>
                  <span className="text-2xl font-bold w-8 text-center">{postsPerWeek}</span>
                  <Button
                    variant="outline" size="icon"
                    onClick={() => setPostsPerWeek(Math.min(7, postsPerWeek + 1))}
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {/* Formats */}
              <div className="space-y-2">
                <label className="text-sm font-semibold">Allowed Formats</label>
                <div className="flex gap-2 flex-wrap">
                  {FORMATS.map(f => (
                    <button
                      key={f}
                      onClick={() => toggleFormat(f)}
                      className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border font-medium transition-colors ${
                        selectedFormats.includes(f)
                          ? FORMAT_COLORS[f]
                          : "border-muted text-muted-foreground hover:border-foreground/30"
                      }`}
                    >
                      {FORMAT_ICONS[f]}
                      {f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Error */}
              {mutation.isError && (
                <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded p-2.5">
                  {(mutation.error as Error).message}
                </div>
              )}
            </>
          ) : (
            /* Results view */
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
                <span className="font-medium">{result.message}</span>
              </div>
              <div className="space-y-2">
                {result.posts.map(p => (
                  <DraftPostCard key={p.id} post={p} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer CTA */}
        <div className="p-5 border-t space-y-2">
          {!result ? (
            <Button
              className="w-full gap-2 bg-purple-600 hover:bg-purple-500 text-white"
              disabled={mutation.isPending || pillars.every(p => !p.trim())}
              onClick={() => mutation.mutate()}
            >
              {mutation.isPending ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Generating your week...</>
              ) : (
                <><Sparkles className="h-4 w-4" /> Generate {postsPerWeek} Posts</>
              )}
            </Button>
          ) : (
            <>
              <Button
                className="w-full gap-2"
                variant="outline"
                onClick={() => { setResult(null); setPillars(["", "", ""]); }}
              >
                Generate Another Week
              </Button>
              <Button className="w-full gap-2" onClick={onClose}>
                <CheckCircle2 className="h-4 w-4" /> Done — View Calendar
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { api, apiV2 } from "@/lib/api"
import { toast } from "sonner"

// ── Types ─────────────────────────────────────────────────────────────────────

interface ScoreBreakdown {
  hook_strength: number    // 0-30
  readability: number      // 0-20
  value_density: number    // 0-30
  cta_quality: number      // 0-20
}

interface HookAlternative {
  hook: string
  predicted_score: number
}

interface ViralityData {
  virality_score: number | null
  score_breakdown: ScoreBreakdown | null
  hook_alternatives: HookAlternative[]
  score_updated_at: string | null
}

interface Props {
  postId: string
  initialData?: ViralityData | null
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getScoreColor(score: number): { ring: string; bg: string; text: string; label: string } {
  if (score >= 80) return { ring: "#22c55e", bg: "rgba(34,197,94,0.1)", text: "#22c55e", label: "🔥 Viral" }
  if (score >= 60) return { ring: "#3b82f6", bg: "rgba(59,130,246,0.1)", text: "#3b82f6", label: "✨ Strong" }
  if (score >= 40) return { ring: "#f59e0b", bg: "rgba(245,158,11,0.1)", text: "#f59e0b", label: "⚡ Average" }
  return { ring: "#ef4444", bg: "rgba(239,68,68,0.08)", text: "#ef4444", label: "🔧 Needs Work" }
}

function ScoreRing({ score }: { score: number }) {
  const r = 42
  const circ = 2 * Math.PI * r
  const filled = (score / 100) * circ
  const colors = getScoreColor(score)

  return (
    <div style={{ position: "relative", width: 108, height: 108 }}>
      <svg width={108} height={108} style={{ transform: "rotate(-90deg)" }}>
        {/* Track */}
        <circle cx={54} cy={54} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={10} />
        {/* Fill */}
        <circle
          cx={54} cy={54} r={r}
          fill="none"
          stroke={colors.ring}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circ}`}
          style={{ transition: "stroke-dasharray 1s cubic-bezier(.4,0,.2,1)", filter: `drop-shadow(0 0 6px ${colors.ring})` }}
        />
      </svg>
      <div style={{
        position: "absolute", inset: 0,
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center"
      }}>
        <span style={{ fontSize: 26, fontWeight: 800, color: colors.ring, lineHeight: 1 }}>{score}</span>
        <span style={{ fontSize: 10, color: "rgba(255,255,255,0.45)", fontWeight: 600, letterSpacing: "0.05em" }}>/100</span>
      </div>
    </div>
  )
}

function DimBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.round((value / max) * 100)
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "rgba(255,255,255,0.55)", fontWeight: 500 }}>
        <span>{label}</span>
        <span style={{ color: "rgba(255,255,255,0.8)", fontWeight: 700 }}>{value}/{max}</span>
      </div>
      <div style={{ background: "rgba(255,255,255,0.08)", borderRadius: 99, height: 5, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${pct}%`, borderRadius: 99,
          background: color,
          transition: "width 0.8s cubic-bezier(.4,0,.2,1)",
          boxShadow: `0 0 8px ${color}88`,
        }} />
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export function ViralityBadge({ postId, initialData }: Props) {
  const [data, setData] = useState<ViralityData | null>(initialData ?? null)
  const [expanded, setExpanded] = useState(false)
  const [selectedHook, setSelectedHook] = useState<string | null>(null)

  const scoreMutation = useMutation({
    mutationFn: async () => {
      const res = await apiV2.post(`/posts/${postId}/score`)
      return res.data as ViralityData
    },
    onSuccess: (res) => {
      setData(res)
      setExpanded(true)
      toast.success(`Virality score: ${res.virality_score}/100`)
    },
    onError: () => toast.error("Scoring failed — check AI Engine"),
  })

  const hasScore = data?.virality_score != null
  const colors = hasScore ? getScoreColor(data!.virality_score!) : null

  // ── Pre-score state ────────────────────────────────────────────────────────
  if (!hasScore) {
    return (
      <div style={{
        background: "linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.08))",
        border: "1px solid rgba(99,102,241,0.25)",
        borderRadius: 16,
        padding: "20px 24px",
        display: "flex",
        alignItems: "center",
        gap: 16,
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: 12,
          background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 22, flexShrink: 0,
          boxShadow: "0 4px 20px rgba(99,102,241,0.4)",
        }}>⚡</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: "rgba(255,255,255,0.9)", marginBottom: 2 }}>
            Virality Score Engine
          </div>
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>
            AI scores this draft 0-100 with hook alternatives
          </div>
        </div>
        <button
          id="score-post-btn"
          onClick={() => scoreMutation.mutate()}
          disabled={scoreMutation.isPending}
          style={{
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            border: "none",
            borderRadius: 10,
            color: "#fff",
            fontWeight: 700,
            fontSize: 13,
            padding: "10px 18px",
            cursor: scoreMutation.isPending ? "not-allowed" : "pointer",
            opacity: scoreMutation.isPending ? 0.7 : 1,
            transition: "all 0.2s",
            whiteSpace: "nowrap",
            boxShadow: "0 4px 14px rgba(99,102,241,0.3)",
          }}
        >
          {scoreMutation.isPending ? "Scoring..." : "Score it →"}
        </button>
      </div>
    )
  }

  const score = data!.virality_score!
  const bd = data!.score_breakdown

  // ── Scored state ───────────────────────────────────────────────────────────
  return (
    <div style={{
      background: `linear-gradient(135deg, ${colors!.bg}, rgba(255,255,255,0.03))`,
      border: `1px solid ${colors!.ring}44`,
      borderRadius: 16,
      overflow: "hidden",
      transition: "box-shadow 0.3s",
      boxShadow: `0 4px 24px ${colors!.ring}22`,
    }}>
      {/* Header row */}
      <button
        id="virality-badge-toggle"
        onClick={() => setExpanded(e => !e)}
        style={{
          width: "100%", background: "none", border: "none",
          display: "flex", alignItems: "center", gap: 16,
          padding: "16px 20px", cursor: "pointer", textAlign: "left",
        }}
      >
        <ScoreRing score={score} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: "rgba(255,255,255,0.95)", marginBottom: 4 }}>
            Virality Score
          </div>
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            background: `${colors!.ring}22`, borderRadius: 8,
            padding: "3px 10px", fontSize: 12, fontWeight: 700, color: colors!.text,
          }}>
            {colors!.label}
          </div>
          {data!.score_updated_at && (
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", marginTop: 6 }}>
              Scored {new Date(data!.score_updated_at).toLocaleTimeString()}
            </div>
          )}
        </div>
        <div style={{
          fontSize: 11, color: "rgba(255,255,255,0.35)", fontWeight: 600,
          display: "flex", alignItems: "center", gap: 4, flexShrink: 0,
        }}>
          {expanded ? "▲ Collapse" : "▼ Details"}
        </div>
      </button>

      {/* Expandable breakdown */}
      {expanded && (
        <div style={{ padding: "0 20px 20px", display: "flex", flexDirection: "column", gap: 20 }}>
          <hr style={{ borderColor: "rgba(255,255,255,0.07)", margin: 0 }} />

          {/* Dimension bars */}
          {bd && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "rgba(255,255,255,0.5)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 2 }}>
                Score Breakdown
              </div>
              <DimBar label="Hook Strength" value={bd.hook_strength} max={30} color="#f59e0b" />
              <DimBar label="Readability" value={bd.readability} max={20} color="#3b82f6" />
              <DimBar label="Value Density" value={bd.value_density} max={30} color="#8b5cf6" />
              <DimBar label="CTA Quality" value={bd.cta_quality} max={20} color="#22c55e" />
            </div>
          )}

          {/* Hook alternatives */}
          {data!.hook_alternatives?.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "rgba(255,255,255,0.5)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 2 }}>
                3 Stronger Hooks (click to copy)
              </div>
              {data!.hook_alternatives.map((alt, i) => (
                <button
                  key={i}
                  id={`hook-alt-${i}`}
                  onClick={() => {
                    navigator.clipboard.writeText(alt.hook)
                    setSelectedHook(alt.hook)
                    toast.success("Hook copied to clipboard!")
                  }}
                  style={{
                    background: selectedHook === alt.hook
                      ? "rgba(99,102,241,0.2)"
                      : "rgba(255,255,255,0.04)",
                    border: `1px solid ${selectedHook === alt.hook ? "#6366f1" : "rgba(255,255,255,0.08)"}`,
                    borderRadius: 10,
                    padding: "10px 14px",
                    textAlign: "left",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    transition: "all 0.15s",
                  }}
                >
                  <span style={{
                    background: "rgba(99,102,241,0.3)", color: "#a5b4fc",
                    borderRadius: 6, padding: "2px 7px", fontSize: 11,
                    fontWeight: 700, flexShrink: 0, marginTop: 1,
                  }}>
                    {alt.predicted_score}
                  </span>
                  <span style={{ fontSize: 13, color: "rgba(255,255,255,0.8)", lineHeight: 1.5 }}>
                    {alt.hook}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Re-score button */}
          <button
            id="rescore-post-btn"
            onClick={() => scoreMutation.mutate()}
            disabled={scoreMutation.isPending}
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8, color: "rgba(255,255,255,0.5)",
              fontSize: 12, fontWeight: 600, padding: "8px 14px",
              cursor: scoreMutation.isPending ? "not-allowed" : "pointer",
              alignSelf: "flex-start",
              transition: "all 0.15s",
            }}
          >
            {scoreMutation.isPending ? "Re-scoring..." : "↻ Re-score"}
          </button>
        </div>
      )}
    </div>
  )
}

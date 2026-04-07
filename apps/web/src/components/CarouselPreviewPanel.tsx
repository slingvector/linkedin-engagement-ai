"use client"

import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api, apiV2 } from "@/lib/api"
import { toast } from "sonner"

// ── Types ─────────────────────────────────────────────────────────────────────

interface Slide {
  slide_number: number
  headline: string
  body: string
  visual_suggestion: string
}

interface CarouselAsset {
  id: string
  post_id: string
  slide_count: number
  slides: Slide[]
  pdf_url: string | null
  status: string
  linkedin_asset_urn: string | null
  brand_kit: Record<string, string> | null
  created_at: string
}

interface Props {
  postId: string
  postCaption?: string   // Hook + body merged for LinkedIn caption
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SlideCard({
  slide,
  isActive,
  onClick,
  brandColor = "#0A66C2",
}: {
  slide: Slide
  isActive: boolean
  onClick: () => void
  brandColor?: string
}) {
  const isCover = slide.slide_number === 1

  return (
    <button
      id={`slide-card-${slide.slide_number}`}
      onClick={onClick}
      style={{
        width: 180,
        height: 180,
        borderRadius: 14,
        border: isActive ? `2px solid ${brandColor}` : "2px solid rgba(255,255,255,0.07)",
        background: isActive
          ? `linear-gradient(135deg, ${brandColor}22, rgba(255,255,255,0.04))`
          : "rgba(255,255,255,0.03)",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        padding: 16,
        textAlign: "left",
        transition: "all 0.15s",
        flexShrink: 0,
        position: "relative",
        overflow: "hidden",
        boxShadow: isActive ? `0 0 20px ${brandColor}33` : "none",
      }}
    >
      {/* Top accent bar */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0,
        height: 4, background: brandColor, opacity: isCover ? 1 : 0.4,
      }} />

      {/* Slide number */}
      <div style={{
        fontSize: 10, fontWeight: 700, color: brandColor,
        letterSpacing: "0.1em", marginBottom: 8, marginTop: 6,
        textTransform: "uppercase",
      }}>
        {isCover ? "COVER" : `SLIDE ${slide.slide_number}`}
      </div>

      {/* Headline */}
      <div style={{
        fontSize: 12, fontWeight: 700, color: "rgba(255,255,255,0.9)",
        lineHeight: 1.3, overflow: "hidden",
        display: "-webkit-box",
        WebkitLineClamp: 3,
        WebkitBoxOrient: "vertical",
      }}>
        {slide.headline}
      </div>
    </button>
  )
}

function SlideDetail({ slide, brandColor = "#0A66C2" }: { slide: Slide; brandColor?: string }) {
  return (
    <div style={{
      background: "#0f172a",
      borderRadius: 20,
      overflow: "hidden",
      border: "1px solid rgba(255,255,255,0.07)",
      display: "flex",
      flexDirection: "column",
      minHeight: 400,
    }}>
      {/* Top accent bar */}
      <div style={{ height: 6, background: brandColor }} />

      <div style={{ padding: "32px 36px", flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Slide number label */}
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8,
        }}>
          <div style={{
            background: `${brandColor}22`, border: `1px solid ${brandColor}44`,
            borderRadius: 8, padding: "4px 10px",
            fontSize: 11, fontWeight: 700, color: brandColor,
            letterSpacing: "0.08em", textTransform: "uppercase",
          }}>
            {slide.slide_number === 1 ? "Cover Slide" : `Slide ${slide.slide_number}`}
          </div>
        </div>

        {/* Headline */}
        <div style={{ fontSize: 28, fontWeight: 800, color: "#f8fafc", lineHeight: 1.2, letterSpacing: "-0.5px" }}>
          {slide.headline}
        </div>

        {/* Body */}
        <div style={{ fontSize: 15, color: "rgba(248,250,252,0.65)", lineHeight: 1.7 }}>
          {slide.body}
        </div>

        {/* Visual hint */}
        <div style={{
          borderLeft: `3px solid ${brandColor}55`,
          paddingLeft: 14,
          fontSize: 13,
          color: "rgba(248,250,252,0.35)",
          fontStyle: "italic",
        }}>
          💡 {slide.visual_suggestion}
        </div>
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export function CarouselPreviewPanel({ postId, postCaption = "" }: Props) {
  const [activeSlide, setActiveSlide] = useState(0)
  const [caption, setCaption] = useState(postCaption)
  const [needsWriteAuth, setNeedsWriteAuth] = useState(false)
  const queryClient = useQueryClient()

  // ── Fetch existing carousel ───────────────────────────────────────────────
  const { data: asset, isLoading: fetchLoading } = useQuery<CarouselAsset>({
    queryKey: ["carousel", postId],
    queryFn: async () => {
      const res = await apiV2.get(`/posts/${postId}/carousel`)
      return res.data
    },
    retry: false,
  })

  // ── Generate carousel ─────────────────────────────────────────────────────
  const generateMutation = useMutation({
    mutationFn: async () => {
      const res = await apiV2.post(`/posts/${postId}/carousel`)
      return res.data as CarouselAsset
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["carousel", postId], data)
      setActiveSlide(0)
      toast.success(`${data.slide_count} slides generated!`)
    },
    onError: () => toast.error("Carousel generation failed"),
  })

  // ── Publish to LinkedIn ───────────────────────────────────────────────────
  const publishMutation = useMutation({
    mutationFn: async () => {
      const res = await apiV2.post(`/posts/${postId}/carousel/publish`, {
        post_text: caption,
      })
      return res.data
    },
    onSuccess: () => {
      toast.success("Carousel published to LinkedIn! 🚀")
      setNeedsWriteAuth(false)
      queryClient.invalidateQueries({ queryKey: ["carousel", postId] })
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      if (detail === "write_flow_not_connected" || (typeof detail === "string" && detail.includes("token expired"))) {
        setNeedsWriteAuth(true)
        toast.error("LinkedIn Write Access required")
      } else {
        toast.error(typeof detail === "string" ? detail : "LinkedIn publish failed")
      }
    },
  })

  // ── Handle Auth Redirect ──────────────────────────────────────────────────
  const handleConnectWriteFlow = async () => {
    try {
      const res = await apiV2.get("/auth/linkedin")
      if (res.data?.auth_url) {
        window.location.href = res.data.auth_url
      }
    } catch (err) {
      toast.error("Failed to initiate LinkedIn connection")
    }
  }

  const brandColor = asset?.brand_kit?.primary_color ?? "#0A66C2"
  const slides = asset?.slides ?? []
  const currentSlide = slides[activeSlide]

  // ── Pre-generation state ──────────────────────────────────────────────────
  if (!asset && !fetchLoading) {
    return (
      <div style={{
        background: "linear-gradient(135deg, rgba(10,102,194,0.1), rgba(255,255,255,0.03))",
        border: "1px solid rgba(10,102,194,0.2)",
        borderRadius: 18,
        padding: "24px 28px",
        display: "flex",
        alignItems: "center",
        gap: 18,
      }}>
        <div style={{
          width: 52, height: 52, borderRadius: 14, flexShrink: 0,
          background: "linear-gradient(135deg, #0A66C2, #0052a3)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 24, boxShadow: "0 4px 20px rgba(10,102,194,0.4)",
        }}>
          🎠
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: "rgba(255,255,255,0.9)", marginBottom: 3 }}>
            Carousel Studio
          </div>
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)" }}>
            Turn this post into a swipeable 7-slide LinkedIn carousel
          </div>
        </div>
        <button
          id="generate-carousel-btn"
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          style={{
            background: "linear-gradient(135deg, #0A66C2, #0052a3)",
            border: "none", borderRadius: 12, color: "#fff",
            fontWeight: 700, fontSize: 13, padding: "12px 20px",
            cursor: generateMutation.isPending ? "not-allowed" : "pointer",
            opacity: generateMutation.isPending ? 0.7 : 1,
            whiteSpace: "nowrap",
            boxShadow: "0 4px 16px rgba(10,102,194,0.35)",
            transition: "all 0.2s",
          }}
        >
          {generateMutation.isPending ? "Generating..." : "✨ Make Carousel"}
        </button>
      </div>
    )
  }

  if (fetchLoading || !asset) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "rgba(255,255,255,0.3)", fontSize: 13 }}>
        Loading carousel...
      </div>
    )
  }

  // ── Carousel preview ──────────────────────────────────────────────────────
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: "rgba(255,255,255,0.9)" }}>
            Carousel Preview
          </div>
          <div style={{
            background: `${brandColor}22`, border: `1px solid ${brandColor}44`,
            borderRadius: 8, padding: "2px 10px",
            fontSize: 11, fontWeight: 700, color: brandColor,
          }}>
            {asset.slide_count} slides · {asset.status}
          </div>
        </div>
        <button
          id="regenerate-carousel-btn"
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8, color: "rgba(255,255,255,0.5)",
            fontSize: 12, fontWeight: 600, padding: "6px 12px",
            cursor: "pointer", transition: "all 0.15s",
          }}
        >
          {generateMutation.isPending ? "Regenerating..." : "↻ Regenerate"}
        </button>
      </div>

      {/* Slide strip (horizontal scroll) */}
      <div style={{
        display: "flex", gap: 10, overflowX: "auto", paddingBottom: 8,
        scrollbarWidth: "thin",
      }}>
        {slides.map((slide, i) => (
          <SlideCard
            key={slide.slide_number}
            slide={slide}
            isActive={i === activeSlide}
            onClick={() => setActiveSlide(i)}
            brandColor={brandColor}
          />
        ))}
      </div>

      {/* Active slide detail */}
      {currentSlide && (
        <SlideDetail slide={currentSlide} brandColor={brandColor} />
      )}

      {/* Slide navigator dots */}
      <div style={{ display: "flex", justifyContent: "center", gap: 6 }}>
        {slides.map((_, i) => (
          <button
            key={i}
            id={`slide-dot-${i}`}
            onClick={() => setActiveSlide(i)}
            style={{
              width: i === activeSlide ? 20 : 6,
              height: 6, borderRadius: 99,
              background: i === activeSlide ? brandColor : "rgba(255,255,255,0.15)",
              border: "none", cursor: "pointer",
              transition: "all 0.2s",
            }}
          />
        ))}
      </div>

      {/* Publish section */}
      <div style={{
        borderTop: "1px solid rgba(255,255,255,0.07)",
        paddingTop: 20,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "rgba(255,255,255,0.45)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          LinkedIn Post Caption
        </div>
        <textarea
          id="carousel-caption-input"
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          placeholder="Add your post caption (the text above the carousel on LinkedIn)..."
          rows={4}
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.09)",
            borderRadius: 10, color: "rgba(255,255,255,0.8)",
            fontSize: 13, padding: "12px 14px", resize: "vertical",
            outline: "none", fontFamily: "inherit", lineHeight: 1.6,
            width: "100%",
          }}
        />
        {needsWriteAuth ? (
          <button
            id="connect-write-flow-btn"
            onClick={handleConnectWriteFlow}
            style={{
              background: "#000",
              border: "1px solid #0A66C2",
              borderRadius: 12, color: "#0A66C2", fontWeight: 700, fontSize: 14,
              padding: "14px 24px", cursor: "pointer",
              transition: "all 0.2s",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            }}
          >
            🔑 Connect LinkedIn Publishing Access
          </button>
        ) : (
          <button
            id="publish-carousel-btn"
            onClick={() => publishMutation.mutate()}
            disabled={publishMutation.isPending || !caption.trim() || asset.status === "published"}
            style={{
              background: asset.status === "published"
                ? "rgba(34,197,94,0.2)"
                : "linear-gradient(135deg, #0A66C2, #0052a3)",
              border: asset.status === "published" ? "1px solid rgba(34,197,94,0.3)" : "none",
              borderRadius: 12, color: "#fff", fontWeight: 700, fontSize: 14,
              padding: "14px 24px", cursor: publishMutation.isPending || asset.status === "published" ? "not-allowed" : "pointer",
              opacity: publishMutation.isPending ? 0.7 : 1,
              boxShadow: asset.status === "published" ? "none" : "0 4px 20px rgba(10,102,194,0.4)",
              transition: "all 0.2s",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            }}
          >
            {publishMutation.isPending
              ? "Publishing..."
              : asset.status === "published"
              ? "✅ Published to LinkedIn"
              : "🚀 Publish Carousel to LinkedIn"}
          </button>
        )}
      </div>
    </div>
  )
}

"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export type HeatmapData = {
  heatmap: Record<string, Record<string, number>>
  best_slots: Array<{ day: string; hour: number; avg_engagement_rate: number }>
  worst_slots: Array<{ day: string; hour: number; avg_engagement_rate: number }>
  data_source: "personal" | "global_benchmark"
  sample_size: number
}

export function useHeatmap(weeks = 8) {
  return useQuery<HeatmapData>({
    queryKey: ["heatmap", weeks],
    queryFn: async () => {
      const res = await api.get(`/api/v2/analytics/heatmap?weeks=${weeks}`)
      return res.data
    },
    staleTime: 1000 * 60 * 30, // 30 min — heatmap is stable
  })
}

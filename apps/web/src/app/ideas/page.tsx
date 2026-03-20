"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { useRouter } from "next/navigation"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card"
import { Lightbulb, PenTool, ArrowRight } from "lucide-react"

export default function IdeasPage() {
  const router = useRouter()
  const [audience, setAudience] = useState("")
  const [niche, setNiche] = useState("")
  const [ideas, setIdeas] = useState<any[]>([])

  const generateIdeas = useMutation({
    mutationFn: async () => {
      const res = await api.post("/ideas/generate", {
        target_audience: audience,
        topic_niche: niche,
      })
      return res.data.items
    },
    onSuccess: (data) => {
      setIdeas(data)
      toast.success("Generated 5 fresh content ideas!")
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to generate ideas")
    },
  })

  // When clicking an idea, pass it via URL parameters to the Post Creator
  const handleDraftPost = (ideaObj: any) => {
    const params = new URLSearchParams()
    params.set("audience", audience)
    params.set("topic", ideaObj.idea)
    router.push(`/posts?${params.toString()}`)
  }

  return (
    <div className="flex flex-col h-full p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight inline-flex items-center gap-2">
          <Lightbulb className="h-8 w-8 text-amber-500" />
          Idea Engine
        </h1>
        <p className="text-muted-foreground mt-2">
          Input your target audience and niche to generate highly-clickable post angles.
        </p>
      </div>

      <Card className="border-muted bg-muted/20">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="flex-1 space-y-2">
              <Label htmlFor="audience">Target Audience</Label>
              <Input
                id="audience"
                placeholder="e.g. B2B SaaS Founders..."
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
              />
            </div>
            
            <div className="flex-1 space-y-2">
              <Label htmlFor="niche">Core Topic / Niche</Label>
              <Input
                id="niche"
                placeholder="e.g. Bootstrapping vs VC Funding..."
                value={niche}
                onChange={(e) => setNiche(e.target.value)}
              />
            </div>

            <Button 
              className="w-full md:w-auto px-8" 
              onClick={() => generateIdeas.mutate()}
              disabled={generateIdeas.isPending || !audience || !niche}
            >
              {generateIdeas.isPending ? "Brainstorming..." : "Generate 5 Ideas"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {ideas.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-4">
          {ideas.map((item, i) => (
            <Card key={i} className="flex flex-col hover:shadow-md transition-shadow border-muted">
              <CardHeader className="pb-3">
                <CardDescription className="text-xs font-semibold uppercase tracking-wider text-amber-600">
                  Angle {i + 1}
                </CardDescription>
                <CardTitle className="text-lg leading-tight mt-1">
                  {item.idea}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 text-sm text-foreground/80">
                {item.angle}
              </CardContent>
              <CardFooter className="pt-2">
                <Button 
                  variant="secondary" 
                  className="w-full text-xs" 
                  onClick={() => handleDraftPost(item)}
                >
                  <PenTool className="mr-2 h-3 w-3" /> Start Drafting <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

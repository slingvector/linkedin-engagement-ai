"use client"

import { useState, useEffect, Suspense } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { useSearchParams } from "next/navigation"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

function PostCreatorContent() {
  const searchParams = useSearchParams()
  const initialTopic = searchParams.get("topic") || ""
  const initialAudience = searchParams.get("audience") || ""

  const [topic, setTopic] = useState(initialTopic)
  const [audience, setAudience] = useState(initialAudience)
  const [framework, setFramework] = useState("story")
  const [generatedPost, setGeneratedPost] = useState<any>(null)

  // Update state if URL changes (like clicking from Idea Generator back into here)
  useEffect(() => {
    if (initialTopic) setTopic(initialTopic)
    if (initialAudience) setAudience(initialAudience)
  }, [initialTopic, initialAudience])

  const queryClient = useQueryClient()

  // Generate Post Mutation
  const generatePost = useMutation({
    mutationFn: async () => {
      const res = await api.post("/posts/generate", {
        topic,
        audience,
        framework,
        tone: "professional_but_conversational", // Hardcoded default here to keep UI clean
      })
      return res.data
    },
    onSuccess: (data) => {
      setGeneratedPost(data)
      toast.success("Post generated successfully!")
      queryClient.invalidateQueries({ queryKey: ["posts"] })
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail;
      const errorMessage = Array.isArray(detail) ? detail[0]?.msg : (typeof detail === 'string' ? detail : "Failed to generate post");
      toast.error(errorMessage);
    },
  })

  // Schedule Post Mutation
  const schedulePost = useMutation({
    mutationFn: async ({ postId, scheduledAt }: { postId: string, scheduledAt: string }) => {
      const res = await api.patch(`/posts/${postId}/schedule`, {
        scheduled_at: scheduledAt
      })
      return res.data
    },
    onSuccess: (data) => {
      setGeneratedPost(data)
      toast.success("Post scheduled successfully!")
      queryClient.invalidateQueries({ queryKey: ["posts-calendar"] })
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail;
      const errorMessage = Array.isArray(detail) ? detail[0]?.msg : (typeof detail === 'string' ? detail : "Failed to schedule post");
      toast.error(errorMessage);
    },
  })

  const isGenerating = generatePost.isPending

  const handleSchedule = () => {
    if (!generatedPost?.id) return
    // Mock scheduling for 1 minute from now to test worker easily
    const targetTime = new Date(Date.now() + 60 * 1000).toISOString()
    schedulePost.mutate({ postId: generatedPost.id, scheduledAt: targetTime })
  }

  return (
    <div className="flex h-full flex-col p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Post Creator</h1>
        <p className="text-muted-foreground mt-2">
          Use AI to ghostwrite high-converting LinkedIn posts based on proven frameworks.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Sidebar Config */}
        <Card className="col-span-1 border-muted">
          <CardHeader>
            <CardTitle className="text-lg">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="topic">Topic / Core Idea</Label>
              <Input
                id="topic"
                placeholder="e.g. Remote work vs RTO..."
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="audience">Target Audience</Label>
              <Input
                id="audience"
                placeholder="e.g. Startup Founders..."
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Framework</Label>
              <Select value={framework} onValueChange={(val) => setFramework(val || "story")}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a framework" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="story">Personal Story</SelectItem>
                  <SelectItem value="contrarian">Contrarian Take</SelectItem>
                  <SelectItem value="playbook">Step-by-Step Playbook</SelectItem>
                  <SelectItem value="lessons">Hard-earned Lessons</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button 
              className="w-full mt-4" 
              onClick={() => generatePost.mutate()}
              disabled={isGenerating || !topic || !audience}
            >
              {isGenerating ? "Generating..." : "Generate Post"}
            </Button>
          </CardContent>
        </Card>

        {/* Editor Canvas */}
        <Card className="col-span-1 md:col-span-2 border-muted h-full flex flex-col">
          <CardHeader>
            <CardTitle className="text-lg">Editor Canvas</CardTitle>
          </CardHeader>
          <CardContent className="flex-1">
            {generatedPost ? (
              <div className="space-y-6">
                <div className="space-y-2">
                  <Label>The Hook</Label>
                  <Textarea 
                    className="min-h-[80px] font-medium resize-none shadow-sm"
                    defaultValue={generatedPost.hook}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Body Content</Label>
                  <Textarea 
                    className="min-h-[250px] shadow-sm whitespace-pre-wrap"
                    defaultValue={generatedPost.body_content}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Call to Action (CTA)</Label>
                  <Input 
                    className="font-medium shadow-sm"
                    defaultValue={generatedPost.call_to_action}
                  />
                </div>
                <div className="flex gap-4 pt-4">
                  <Button variant="outline" className="w-full">Save Draft</Button>
                  <Button 
                    className="w-full bg-blue-600 hover:bg-blue-700" 
                    onClick={handleSchedule}
                    disabled={schedulePost.isPending || generatedPost.status === 'scheduled'}
                  >
                    {generatedPost.status === 'scheduled' ? "Scheduled" : schedulePost.isPending ? "Scheduling..." : "Schedule (1m from now)"}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex h-[400px] items-center justify-center border-2 border-dashed rounded-md text-muted-foreground text-sm">
                Fill out the configuration and generate a post to see it here.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function PostCreatorPage() {
  return (
    <Suspense fallback={<div className="p-6">Loading editor...</div>}>
      <PostCreatorContent />
    </Suspense>
  )
}

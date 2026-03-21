"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"
import { Plus, MessageSquare, Briefcase, Zap, CheckCircle2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"

export default function RadarPage() {
  const queryClient = useQueryClient()
  const [newCreatorUrl, setNewCreatorUrl] = useState("")
  const [editedComment, setEditedComment] = useState<Record<string, string>>({})
  const [generatedDrafts, setGeneratedDrafts] = useState<Record<string, any>>({})

  // Fetch Feed
  const { data: feedData, isLoading: feedLoading } = useQuery({
    queryKey: ["radar-feed"],
    queryFn: async () => {
      const res = await api.get("/copilot/feed")
      return res.data.items || []
    }
  })

  // Add Creator
  const addCreator = useMutation({
    mutationFn: async (url: string) => {
      const res = await api.post("/radar/creators", { profile_url: url })
      return res.data
    },
    onSuccess: () => {
      toast.success("Creator added to radar")
      setNewCreatorUrl("")
      queryClient.invalidateQueries({ queryKey: ["radar-feed"] })
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "Failed to add creator")
  })

  // Generate Comments
  const generateComments = useMutation({
    mutationFn: async (postId: string) => {
      const res = await api.post("/copilot/generate", { ingested_post_id: postId })
      return { postId, drafts: res.data }
    },
    onSuccess: ({ postId, drafts }: { postId: string, drafts: any }) => {
      toast.success("Comment strategies generated!")
      setGeneratedDrafts(prev => ({ ...prev, [postId]: drafts }))
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "Failed to generate comments")
  })

  // Submit Feedback
  const submitFeedback = useMutation({
    mutationFn: async ({ postId, original, edited }: { postId: string, original: string, edited: string }) => {
      await api.post("/comments/feedback", {
        post_id: postId,
        original_generated_comment: original,
        final_user_edited_comment: edited,
        was_used: true,
        engagement_likes: 0,
        engagement_replies: 0
      })
    }
  })

  // Copy & Go Workflow
  const handleCopyAndGo = async (postId: string, originalText: string) => {
    const finalText = editedComment[postId] !== undefined ? editedComment[postId] : originalText
    try {
      await navigator.clipboard.writeText(finalText)
      toast.success("Copied & Feedback Tracked!")
      
      // Update status to 'used' and send feedback payload
      submitFeedback.mutate({ postId, original: originalText, edited: finalText })
    } catch (err) {
      toast.error("Failed to copy text")
    }
  }

  return (
    <div className="flex h-full flex-col p-6 space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Creator Radar</h1>
          <p className="text-muted-foreground mt-2">
            Monitor top industry voices and use AI Comment Copilot to ghostwrite targeted replies.
          </p>
        </div>
        <div className="flex z-10 gap-2">
          <Input 
            placeholder="LinkedIn Profile URL..." 
            value={newCreatorUrl}
            onChange={(e) => setNewCreatorUrl(e.target.value)}
            className="w-64"
          />
          <Button 
            onClick={() => addCreator.mutate(newCreatorUrl)}
            disabled={!newCreatorUrl || addCreator.isPending}
          >
            <Plus className="mr-2 h-4 w-4" /> Add to Radar
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <Card className="flex-1 flex flex-col border-muted">
          <CardHeader className="bg-muted/30">
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="h-5 w-5 text-amber-500" />
              Action Desk Feed
            </CardTitle>
            <CardDescription>Latest posts from your tracked creators</CardDescription>
          </CardHeader>
          <Separator />
          <CardContent className="flex-1 p-0 overflow-hidden">
            <ScrollArea className="h-full">
              {feedLoading ? (
                <div className="p-8 text-center text-muted-foreground">Loading feed...</div>
              ) : !feedData || feedData.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  No posts yet. The safe ingestion worker will inject mock posts shortly!
                </div>
              ) : (
                <div className="flex flex-col">
                  {feedData.map((post: any) => (
                    <div key={post.post.id} className="p-6 border-b last:border-b-0 hover:bg-muted/10 transition-colors">
                      <div className="flex items-start gap-4">
                        <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold flex-shrink-0">
                          {post.creator_name.charAt(0)}
                        </div>
                        <div className="flex-1">
                          <div className="flex justify-between items-start">
                            <h3 className="font-semibold">{post.creator_name}</h3>
                            <span className="text-xs text-muted-foreground">
                              {post.post.posted_at ? formatDistanceToNow(new Date(post.post.posted_at)) + " ago" : "Recently"}
                            </span>
                          </div>
                          
                          <p className="mt-2 text-sm whitespace-pre-wrap">{post.post.content}</p>
                          
                          <div className="mt-4 flex gap-[10px] items-center text-xs text-muted-foreground">
                            <span>👍 {post.post.likes}</span>
                            <span>💬 {post.post.comments}</span>
                            <span>•</span>
                            <a href={post.post.post_url} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline">
                              View original post
                            </a>
                          </div>

                          {/* Copilot Section */}
                          <div className="mt-6">
                            {generatedDrafts[post.post.id] ? (
                              <div className="space-y-4 rounded-lg bg-orange-50/50 p-4 border border-orange-100">
                                <h4 className="flex items-center gap-2 font-medium text-amber-900 text-sm">
                                  <MessageSquare className="h-4 w-4" /> 
                                  AI Copilot Strategies
                                </h4>
                                
                                <div className="grid gap-3">
                                  {/* AI Strategies Display */}
                                  <div className="flex flex-col gap-2 bg-white p-3 rounded shadow-sm text-sm border-l-4 border-l-blue-400">
                                    <span className="text-blue-700 italic font-medium mb-1">Insightful Strategy</span>
                                    <textarea 
                                      className="w-full p-2 border rounded-md text-sm text-slate-800"
                                      rows={3}
                                      defaultValue={generatedDrafts[post.post.id]?.insightful_content}
                                      onChange={(e) => setEditedComment(prev => ({...prev, [`${post.post.id}_insightful`]: e.target.value}))}
                                    />
                                    <div className="flex justify-end mt-1">
                                      <Button size="sm" variant="ghost" onClick={() => handleCopyAndGo(post.post.id, generatedDrafts[post.post.id]?.insightful_content || "")}>
                                        Select & Track
                                      </Button>
                                    </div>
                                  </div>
                                  
                                  <div className="flex flex-col gap-2 bg-white p-3 rounded shadow-sm text-sm border-l-4 border-l-red-400">
                                    <span className="text-red-700 italic font-medium mb-1">Contrarian Strategy</span>
                                    <textarea 
                                      className="w-full p-2 border rounded-md text-sm text-slate-800"
                                      rows={3}
                                      defaultValue={generatedDrafts[post.post.id]?.contrarian_content}
                                      onChange={(e) => setEditedComment(prev => ({...prev, [`${post.post.id}_contrarian`]: e.target.value}))}
                                    />
                                    <div className="flex justify-end mt-1">
                                      <Button size="sm" variant="ghost" onClick={() => handleCopyAndGo(post.post.id, generatedDrafts[post.post.id]?.contrarian_content || "")}>
                                        Select & Track
                                      </Button>
                                    </div>
                                  </div>

                                  <div className="flex flex-col gap-2 bg-white p-3 rounded shadow-sm text-sm border-l-4 border-l-green-400">
                                    <span className="text-green-700 italic font-medium mb-1">Supportive Strategy</span>
                                    <textarea 
                                      className="w-full p-2 border rounded-md text-sm text-slate-800"
                                      rows={3}
                                      defaultValue={generatedDrafts[post.post.id]?.supportive_content}
                                      onChange={(e) => setEditedComment(prev => ({...prev, [`${post.post.id}_supportive`]: e.target.value}))}
                                    />
                                    <div className="flex justify-between items-center mt-2">
                                      <span className="text-xs text-muted-foreground ml-2">Edits route to LLMOps Safety Plane.</span>
                                      <Button size="sm" onClick={() => handleCopyAndGo(post.post.id, generatedDrafts[post.post.id]?.supportive_content || "")}>
                                        Select & Track
                                      </Button>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ) : (
                              <Button 
                                variant="outline" 
                                size="sm" 
                                className="bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100 hover:text-orange-800"
                                onClick={() => generateComments.mutate(post.post.id)}
                                disabled={generateComments.isPending}
                              >
                                {generateComments.isPending ? "Generating Strategies (Ollama)..." : "Generate Comment Strategies"}
                              </Button>
                            )}
                          </div>
                          
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { format, parseISO } from "date-fns"
import { CalendarDays, Clock, FileText, CheckCircle2 } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export default function CalendarPage() {
  // Fetch user posts
  const { data: posts, isLoading } = useQuery({
    queryKey: ["posts-calendar"],
    queryFn: async () => {
      // In a real app we might pass status="scheduled" or handle pagination
      const res = await api.get("/posts?per_page=50")
      return res.data.posts || []
    }
  })

  // Filter and sort for calendar view
  const scheduledPosts = posts?.filter((p: any) => p.status === "scheduled" || p.status === "published") 
    .sort((a: any, b: any) => {
      const dateA = a.scheduled_at ? new Date(a.scheduled_at).getTime() : 0
      const dateB = b.scheduled_at ? new Date(b.scheduled_at).getTime() : 0
      return dateB - dateA // Sort descending by scheduled date
    }) || []

  return (
    <div className="flex flex-col h-full p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight inline-flex items-center gap-2">
          <CalendarDays className="h-8 w-8 text-blue-500" />
          Content Calendar
        </h1>
        <p className="text-muted-foreground mt-2">
          View your scheduled and historically published LinkedIn posts.
        </p>
      </div>

      <div className="flex-1">
        {isLoading ? (
          <div className="text-center p-12 text-muted-foreground">Loading calendar...</div>
        ) : scheduledPosts.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-24 border-2 border-dashed rounded-lg text-muted-foreground">
            <CalendarDays className="h-12 w-12 mb-4 opacity-20" />
            <p>No scheduled posts yet. Head to the Post Creator to draft and schedule content!</p>
          </div>
        ) : (
          <div className="space-y-4 max-w-4xl">
            {scheduledPosts.map((post: any) => (
              <Card key={post.id} className="relative overflow-hidden border-muted">
                <div className={`absolute top-0 left-0 w-1.5 h-full ${post.status === 'published' ? 'bg-green-500' : 'bg-blue-500'}`} />
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        <Badge variant={post.status === 'published' ? 'default' : 'secondary'} className={post.status === 'published' ? 'bg-green-600' : ''}>
                          {post.status.toUpperCase()}
                        </Badge>
                        <span className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                          {post.status === 'published' ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
                          {post.scheduled_at ? format(parseISO(post.scheduled_at), "PPP 'at' p") : "Unknown time"}
                        </span>
                      </div>
                      <h3 className="font-semibold text-lg line-clamp-1">{post.topic}</h3>
                      <p className="text-sm text-muted-foreground line-clamp-2">{post.body_content}</p>
                    </div>
                    
                    {post.status === 'published' && post.published_at && (
                      <div className="flex flex-col items-end justify-center text-xs text-muted-foreground border-l pl-4 md:min-w-[120px]">
                        <span>Published on</span>
                        <span className="font-medium text-foreground">{format(parseISO(post.published_at), "MMM d, h:mm a")}</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

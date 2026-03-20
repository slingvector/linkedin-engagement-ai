"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { ExternalLink, MapPin, DollarSign, Building, Sparkles } from "lucide-react"

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"

export default function JobDiscoveryPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['careerJobs'],
    queryFn: async () => {
      const res = await fetch("http://192.168.31.242:8000/api/v1/career/jobs", {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (!res.ok) throw new Error("Failed to fetch jobs")
      return res.json()
    },
    refetchInterval: 15000 // Polling to see background mock seeders
  })

  // Mock checking AI match accuracy representation visually
  const getMatchColor = (score: number) => {
    if (score >= 90) return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
    if (score >= 75) return "bg-blue-500/10 text-blue-500 border-blue-500/20"
    return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Job Discovery</h2>
        <div className="flex items-center space-x-2">
            <span className="text-sm text-muted-foreground flex items-center">
              <span className="relative flex h-3 w-3 mr-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
              </span>
              Intercepting live job signals...
            </span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mt-4">
        {isLoading ? (
            Array.from({ length: 6 }).map((_, i) => (
                <Card key={i} className="flex flex-col">
                    <CardHeader>
                        <Skeleton className="h-6 w-3/4 mb-2" />
                        <Skeleton className="h-4 w-1/2" />
                    </CardHeader>
                    <CardContent className="flex-1">
                        <Skeleton className="h-20 w-full mb-4" />
                        <div className="flex gap-2">
                            <Skeleton className="h-4 w-16" />
                            <Skeleton className="h-4 w-20" />
                        </div>
                    </CardContent>
                </Card>
            ))
        ) : data?.jobs?.length > 0 ? (
            data.jobs.map((job: any) => (
                <Card key={job.id} className="flex flex-col hover:border-primary/50 transition-colors">
                    <CardHeader className="pb-3">
                        <div className="flex justify-between items-start">
                            <div className="space-y-1">
                                <CardTitle className="text-xl">{job.role_title}</CardTitle>
                                <CardDescription className="flex items-center gap-1 text-sm font-medium">
                                    <Building className="h-3 w-3" /> {job.company_name}
                                </CardDescription>
                            </div>
                            {job.match_score && (
                                <Badge variant="outline" className={`flex gap-1 py-1 ${getMatchColor(job.match_score)}`}>
                                    <Sparkles className="h-3 w-3" />
                                    {Math.round(job.match_score)}% Match
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent className="flex-1 space-y-4">
                        <p className="text-sm text-muted-foreground line-clamp-3">
                            {job.description}
                        </p>
                        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                            {job.location && (
                                <div className="flex items-center gap-1">
                                    <MapPin className="h-3 w-3" /> {job.location}
                                </div>
                            )}
                            {job.salary_range && (
                                <div className="flex items-center gap-1">
                                    <DollarSign className="h-3 w-3" /> {job.salary_range}
                                </div>
                            )}
                        </div>
                    </CardContent>
                    <CardFooter className="pt-4 border-t">
                        <Link href={`/jobs/${job.id}`} className="w-full">
                            <Button className="w-full gap-2" variant="secondary">
                                View Deep Link
                                <ExternalLink className="h-4 w-4" />
                            </Button>
                        </Link>
                    </CardFooter>
                </Card>
            ))
        ) : (
            <div className="col-span-full py-12 text-center text-muted-foreground border-2 border-dashed rounded-lg">
                <Building className="h-8 w-8 mx-auto mb-3 opacity-20" />
                <p>No jobs discovered yet.</p>
                <p className="text-sm">The IIE background worker is actively scanning for matches...</p>
            </div>
        )}
      </div>
    </div>
  )
}

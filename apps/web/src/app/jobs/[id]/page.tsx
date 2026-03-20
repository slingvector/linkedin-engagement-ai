"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { Upload, FileText, CheckCircle, Wand2, ArrowRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function JobApplicationWorkspace() {
  const { id } = useParams()
  
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [resumeId, setResumeId] = useState<string | null>(null)
  const [optimizing, setOptimizing] = useState(false)
  
  const [optimizedData, setOptimizedData] = useState<any>(null)
  const [coverLetter, setCoverLetter] = useState<string>("")

  // Mock Job Data (in reality, fetched via ID)
  const job = {
    title: "Backend Software Engineer",
    company: "Stripe",
    description: "Join our global payments infrastructure team. Solid background in Go or Ruby desired. Must have deep understanding of distributed systems and financial ledgers."
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    
    const formData = new FormData()
    formData.append("file", file)
    
    try {
      // In a real flow, this goes to Core API -> CareerService -> parse_and_store_resume
      const res = await fetch("http://192.168.31.242:8000/api/v1/career/upload-resume", {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: formData
      })
      
      const data = await res.json()
      if (data.resume_id) {
        setResumeId(data.resume_id)
      }
    } catch (error) {
      console.error("Upload failed", error)
    } finally {
      setUploading(false)
    }
  }

  const handleOptimize = async () => {
    setOptimizing(true)
    // Simulate AI Engine processing time
    setTimeout(() => {
      setOptimizedData({
        overall_match_score: 92,
        optimized_bullets: [
          {
            original_point: "Built backend services using Python and APIs.",
            optimized_point: "Engineered high-throughput backend infrastructure in Go, processing 10k+ requests/sec in a distributed microservices environment.",
            reasoning: "Aligns with Stripe's requirement for Go and deep understanding of distributed systems."
          },
          {
            original_point: "Managed database tables and ledgers.",
            optimized_point: "Architected immutable financial ledgers ensuring ACID compliance across concurrent payment transactions.",
            reasoning: "Directly addresses the requirement for 'financial ledgers'."
          }
        ]
      })
      setCoverLetter("Hi Hiring Team,\n\nWhen I saw Stripe's need for scaling distributed financial ledgers, I knew it was the perfect fit. Over the last three years, I engineered high-throughput backend infrastructure in Go, processing 10k+ requests/sec. I've specifically architected immutable ledgers ensuring ACID compliance, which directly aligns with your payment infrastructure goals.\n\nI'd love to bring this distributed systems expertise to Stripe.\n\nBest,\nCandidate")
      setOptimizing(false)
    }, 3000)
  }

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-4rem)] p-4 md:p-8 gap-6 max-w-7xl mx-auto w-full">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Application Workspace</h2>
          <p className="text-muted-foreground mt-1">Tailoring your profile for {job.title} at {job.company}</p>
        </div>
        {resumeId && (
            <Button onClick={handleOptimize} disabled={optimizing} className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white">
                {optimizing ? <Wand2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                {optimizing ? "AI Engine Optimizing..." : "Auto-Tailor Application"}
            </Button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
        
        {/* Left Pane: Job Context & Resume Upload */}
        <div className="space-y-6 flex flex-col min-h-0 overflow-y-auto pr-2 pb-4">
            <Card>
                <CardHeader className="bg-muted/50 pb-4">
                  <CardTitle className="text-xl">{job.company}</CardTitle>
                  <CardDescription className="text-base font-semibold text-foreground">{job.title}</CardDescription>
                </CardHeader>
                <CardContent className="pt-6">
                  <h4 className="font-semibold mb-2">Job Description</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {job.description}
                  </p>
                </CardContent>
            </Card>

            {!resumeId ? (
                <Card className="border-dashed border-2 bg-muted/20">
                    <CardHeader>
                        <CardTitle>Base Resume Setup</CardTitle>
                        <CardDescription>Upload your master PDF resume to establish ground-truth context for the AI Engine.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col items-center justify-center p-8 space-y-4">
                        <label htmlFor="resume-upload" className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-muted/30 hover:bg-muted/50 transition-colors">
                            <div className="flex flex-col items-center justify-center pt-5 pb-6">
                                <Upload className="w-8 h-8 mb-3 text-muted-foreground" />
                                <p className="mb-2 text-sm text-foreground"><span className="font-semibold">Click to upload</span> or drag and drop</p>
                                <p className="text-xs text-muted-foreground">PDF (MAX. 2MB)</p>
                            </div>
                            <input id="resume-upload" type="file" accept=".pdf" className="hidden" onChange={handleFileChange} />
                        </label>
                        {file && <span className="text-sm font-medium text-blue-500">{file.name} attached.</span>}
                        <Button disabled={!file || uploading} onClick={handleUpload} className="w-full">
                            {uploading ? "Extracting Text via PDFPlumber..." : "Upload & Parse Context"}
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <Card className="bg-emerald-500/10 border-emerald-500/30">
                    <CardContent className="flex items-center gap-4 p-6">
                        <div className="bg-emerald-500/20 p-3 rounded-full">
                            <CheckCircle className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <div>
                            <p className="font-semibold text-emerald-700 dark:text-emerald-300">Resume Parsed & Context Stored</p>
                            <p className="text-sm text-emerald-600/80 dark:text-emerald-400/80">The IIE successfully extracted ground-truth text. Ready to tailor.</p>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>

        {/* Right Pane: AI Outputs */}
        <div className="flex flex-col min-h-0 border rounded-xl overflow-hidden bg-card">
            {optimizing ? (
                <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-6">
                    <Wand2 className="h-12 w-12 text-indigo-500 animate-pulse" />
                    <div className="space-y-2 w-3/4 max-w-sm text-center">
                        <p className="font-medium">Orchestrating AI Engine</p>
                        <Progress value={66} className="h-2" />
                        <p className="text-xs text-muted-foreground">Mapping extracted PDF text against {job.title} schema...</p>
                    </div>
                </div>
            ) : optimizedData ? (
                <div className="flex flex-col h-full">
                    <div className="bg-muted/40 p-4 border-b flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <SparklesIcon className="h-5 w-5 text-indigo-500" />
                            <span className="font-semibold">AI Generated Artifacts</span>
                        </div>
                        <div className="px-3 py-1 bg-green-500/10 text-green-600 rounded-full text-xs font-bold border border-green-500/20">
                            {optimizedData.overall_match_score}% Optimized Match
                        </div>
                    </div>
                    
                    <Tabs defaultValue="resume" className="flex-1 flex flex-col min-h-0">
                        <div className="px-4 pt-3 border-b">
                            <TabsList className="grid w-full grid-cols-2">
                                <TabsTrigger value="resume">Tailored Bullets</TabsTrigger>
                                <TabsTrigger value="cover">Cover Letter</TabsTrigger>
                            </TabsList>
                        </div>
                        
                        <TabsContent value="resume" className="flex-1 overflow-y-auto p-4 m-0 space-y-4">
                            {optimizedData.optimized_bullets.map((bullet: any, idx: number) => (
                                <div key={idx} className="p-4 border rounded-lg space-y-3 bg-background">
                                    <div>
                                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Original</p>
                                        <p className="text-sm line-through opacity-70">{bullet.original_point}</p>
                                    </div>
                                    <ArrowRight className="h-4 w-4 text-muted-foreground ml-2" />
                                    <div>
                                        <p className="text-xs font-semibold text-indigo-500 uppercase tracking-wider mb-1">Optimized Hit</p>
                                        <p className="text-sm font-medium">{bullet.optimized_point}</p>
                                    </div>
                                    <div className="bg-muted p-2 rounded text-xs text-muted-foreground border-l-2 border-indigo-400">
                                        <span className="font-semibold text-foreground">AI Reasoning:</span> {bullet.reasoning}
                                    </div>
                                </div>
                            ))}
                        </TabsContent>
                        
                        <TabsContent value="cover" className="flex-1 overflow-y-auto p-4 m-0">
                            <Textarea 
                                className="min-h-[400px] font-sans text-sm leading-relaxed resize-none bg-background focus-visible:ring-indigo-500"
                                value={coverLetter}
                                onChange={(e) => setCoverLetter(e.target.value)}
                            />
                            <div className="mt-4 flex justify-end">
                                <Button className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2">
                                    <CheckCircle className="h-4 w-4" /> Finalize & Save to CRM
                                </Button>
                            </div>
                        </TabsContent>
                    </Tabs>
                </div>
            ) : (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
                    <FileText className="h-16 w-16 mb-4 opacity-20" />
                    <h3 className="text-lg font-medium text-foreground mb-2">Blank AI Workspace</h3>
                    <p className="max-w-xs text-sm">Upload your resume and click Auto-Tailor to generate highly targeted artifacts right here.</p>
                </div>
            )}
        </div>
      </div>
    </div>
  )
}

function SparklesIcon(props: any) {
    return (
        <svg
        {...props}
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        >
        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
        <path d="M5 3v4" />
        <path d="M19 17v4" />
        <path d="M3 5h4" />
        <path d="M17 19h4" />
        </svg>
    )
}

"use client"

import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from "recharts"
import { BarChart, Users, TrendingUp, Presentation, Building2 } from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

async function fetchAbmSignals() {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/enterprise/signals`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) return { data: [] };
  const json = await res.json();
  return json.data;
}

async function fetchProspects() {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/sales/prospects`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) return { data: [] };
  const json = await res.json();
  return json.data;
}

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['analyticsDashboard'],
    queryFn: async () => {
      // Direct fetch to core api 
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analytics/dashboard`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (!res.ok) throw new Error("Failed to fetch analytics")
      return res.json()
    },
    refetchInterval: 10000 // auto refresh every 10s to see the worker mock data fill in
  })

  const { data: prospects = [], isLoading: propsLoading } = useQuery({
    queryKey: ['prospectsAnalytics'],
    queryFn: fetchProspects
  });

  const { data: abmData = [], isLoading: abmLoading } = useQuery({
    queryKey: ['abmAnalytics'],
    queryFn: fetchAbmSignals
  });

  // Calculate Pipeline Value (Mocking $500 Avg Deal Size per Qualified/Won Lead)
  const wonLeads = prospects.length > 0 ? prospects.filter((p: any) => 
    p.intent_score > 75 || p.buying_signal.includes("demo")
  ).length : 0;
  
  const estimatedPipeline = prospects.length * 500;
  const closedRevenue = wonLeads * 500;
  
  // ABM Revenue Assuming $50k ACV Enterprise
  const abmPipelineValue = abmData.length * 50000;

  // Theme colors for Pie Chart
  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#64748b']

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h2>
        <div className="flex items-center space-x-2">
            <span className="text-sm text-muted-foreground flex items-center">
              <span className="relative flex h-3 w-3 mr-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              Live Tracking Active
            </span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {/* Sales ROI Pipeline */}
        <Card className="bg-emerald-500/5 border-emerald-500/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-emerald-800 dark:text-emerald-200">
              Closed Revenue
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">
              {propsLoading ? <Skeleton className="h-8 w-20" /> : 
               `$${closedRevenue.toLocaleString()}`}
            </div>
            <p className="text-xs text-emerald-600/80">
              From {wonLeads} AI-converted deals
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-blue-500/5 border-blue-500/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-blue-800 dark:text-blue-200">
              Active Pipeline Value
            </CardTitle>
            <BarChart className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
              {propsLoading ? <Skeleton className="h-8 w-20" /> : 
               `$${estimatedPipeline.toLocaleString()}`}
            </div>
            <p className="text-xs text-blue-600/80">
              Total intercepted prospects: {prospects.length}
            </p>
          </CardContent>
        </Card>

        {/* Enterprise ABM Metrics */}
        <Card className="bg-indigo-500/5 border-indigo-500/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-indigo-800 dark:text-indigo-200">
              ABM Signal Pipeline
            </CardTitle>
            <Building2 className="h-4 w-4 text-indigo-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-indigo-700 dark:text-indigo-300">
              {abmLoading ? <Skeleton className="h-8 w-20" /> : 
               `$${abmPipelineValue.toLocaleString()}`}
            </div>
            <p className="text-xs text-indigo-600/80">
              From {abmData.length} tracked Target Accounts
            </p>
          </CardContent>
        </Card>

        {/* Existing Content Metrics */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Impressions
            </CardTitle>
            <Presentation className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-20" /> : 
               (data?.timeline?.reduce((acc: number, item: any) => acc + item.impressions, 0) || 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              +20.1% from last month
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Audience Size
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-20" /> : 
               (data?.demographics?.reduce((acc: number, item: any) => acc + item.value, 0) || 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              Unique engagers mapped
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Content Growth</CardTitle>
            <CardDescription>
              A timeline of historical impressions driven by published posts.
            </CardDescription>
          </CardHeader>
          <CardContent className="pl-2">
            {isLoading ? (
              <div className="flex items-center justify-center h-[350px]">
                <Skeleton className="h-full w-full mx-4" />
              </div>
            ) : data?.timeline?.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={data.timeline} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                  <XAxis dataKey="date" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `${value}`} />
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Legend verticalAlign="top" height={36}/>
                  <Line type="monotone" dataKey="impressions" stroke="#3b82f6" strokeWidth={3} activeDot={{ r: 8 }} />
                  <Line type="monotone" dataKey="likes" stroke="#10b981" strokeWidth={2} />
                  <Line type="monotone" dataKey="comments" stroke="#f59e0b" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
                <div className="flex items-center justify-center h-[350px] text-muted-foreground">
                    No timeline metrics recorded yet. Awaiting Background Worker.
                </div>
            )}
          </CardContent>
        </Card>
        
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Audience Demographics</CardTitle>
            <CardDescription>
              AI-driven breakdown of your engager personas.
            </CardDescription>
          </CardHeader>
          <CardContent>
             {isLoading ? (
                <div className="flex items-center justify-center h-[300px]">
                    <Skeleton className="h-[250px] w-[250px] rounded-full" />
                </div>
             ) : data?.demographics?.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                    <Pie
                        data={data.demographics}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                    >
                        {data.demographics.map((entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Pie>
                    <RechartsTooltip 
                        formatter={(value) => [`${value} people`, 'Engagers']}
                        contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                    <Legend layout="horizontal" verticalAlign="bottom" align="center" />
                    </PieChart>
                </ResponsiveContainer>
             ) : (
                <div className="flex items-center justify-center h-[300px] text-muted-foreground text-center px-8">
                    Not enough data. Mock metrics worker is calculating clusters...
                </div>
             )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

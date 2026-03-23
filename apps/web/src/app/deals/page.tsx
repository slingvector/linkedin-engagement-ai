"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import { formatDistanceToNow } from "date-fns";
import { 
  Building2, 
  MessageSquare, 
  UserCircle, 
  Target, 
  DollarSign,
  TrendingUp,
  Clock,
  MoreHorizontal
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const STATUS_COLUMNS = [
  { id: "new_lead", title: "New Lead", color: "bg-slate-100 dark:bg-slate-900 border-slate-200" },
  { id: "contacted", title: "Contacted (DM Sent)", color: "bg-blue-50 dark:bg-blue-950 border-blue-200" },
  { id: "qualified", title: "Qualified & Demo Booking", color: "bg-purple-50 dark:bg-purple-950 border-purple-200" },
  { id: "closed_won", title: "Closed Won", color: "bg-emerald-50 dark:bg-emerald-950 border-emerald-200" },
  { id: "closed_lost", title: "Closed Lost", color: "bg-red-50 dark:bg-red-950 border-red-200" },
];

async function fetchProspects() {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/sales/prospects`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to fetch prospects");
  const json = await res.json();
  return json.data;
}

// Mock conversation fetcher (For UI demo we use prospects and map them mentally)
// In a true deep app we'd fetch the exact Conversation table rows
async function updateConversationStatus(prospectId: string, status: string) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/sales/prospects/${prospectId}/status`, {
    method: "PUT",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}` 
    },
    body: JSON.stringify({ status })
  });
  if (!res.ok) throw new Error("Failed to update status");
  return res.json();
}

export default function DealsKanbanPage() {
  const queryClient = useQueryClient();
  
  // We use initial mock state for UX, but sync with DB if hooked perfectly.
  // Since our leads are created as "new_lead" default but our `/prospects` route 
  // only returns prospects (not conversations directly yet), for the UI Kanban we'll pseudo-map them.
  const { data: rawProspects = [], isLoading } = useQuery({
    queryKey: ["prospects", "deals"],
    queryFn: fetchProspects
  });

  const [boardCards, setBoardCards] = useState<any[]>([]);

  useEffect(() => {
    if (rawProspects.length > 0 && boardCards.length === 0) {
      // Initialize un-mapped prospects to 'new_lead' UI state on load
      setBoardCards(rawProspects.map((p: any) => ({ ...p, ui_status: "new_lead" })));
    } else if (rawProspects.length > boardCards.length) {
       // Append newly seeded leads
       const existingIds = new Set(boardCards.map(b => b.id));
       const newItems = rawProspects.filter((p: any) => !existingIds.has(p.id)).map((p:any) => ({...p, ui_status: "new_lead"}));
       setBoardCards(prev => [...prev, ...newItems]);
    }
  }, [rawProspects]);

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) => updateConversationStatus(id, status),
    onSettled: () => {
      // No strict re-fetch needed if we optimistically updated state.
    }
  });

  const onDragEnd = (result: any) => {
    const { destination, source, draggableId } = result;

    if (!destination) return;
    if (destination.droppableId === source.droppableId && destination.index === source.index) return;

    const newStatus = destination.droppableId;
    
    // Optimistic UI Update
    setBoardCards(prevCards => 
      prevCards.map(card => 
        card.id === draggableId ? { ...card, ui_status: newStatus } : card
      )
    );

    // Persist via AI / API
    updateStatusMutation.mutate({ id: draggableId, status: newStatus });
  };

  if (isLoading) {
    return <div className="p-8">Loading Sales Pipeline...</div>;
  }

  // Calculate generic mock deal metrics
  const activeLeads = boardCards.filter(c => c.ui_status !== 'closed_won' && c.ui_status !== 'closed_lost').length;
  const wonLeads = boardCards.filter(c => c.ui_status === 'closed_won').length;

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)]">
      {/* Header & Metrics */}
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Deals Pipeline</h1>
          <p className="text-muted-foreground">Track and convert social buying signals into revenue.</p>
        </div>
        <div className="flex gap-4">
          <Card className="bg-primary/5 border-primary/20">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="h-10 w-10 bg-primary/20 rounded-full flex items-center justify-center">
                <Target className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground font-medium">Active Pipeline</p>
                <p className="text-2xl font-bold">{activeLeads}</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-emerald-500/5 border-emerald-500/20">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="h-10 w-10 bg-emerald-500/20 rounded-full flex items-center justify-center">
                <DollarSign className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground font-medium">Closed Won</p>
                <p className="text-2xl font-bold">{wonLeads}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Kanban Board Container */}
      <div className="flex-1 overflow-x-auto pb-4">
        <DragDropContext onDragEnd={onDragEnd}>
          <div className="flex h-full gap-4 items-start min-w-[1200px]">
            {STATUS_COLUMNS.map(column => (
              <Droppable key={column.id} droppableId={column.id}>
                {(provided: any, snapshot: any) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={`flex flex-col h-full w-[320px] rounded-xl border p-3 flex-shrink-0 transition-colors ${column.color} ${snapshot.isDraggingOver ? 'ring-2 ring-primary/50' : ''}`}
                  >
                    {/* Column Header */}
                    <div className="flex items-center justify-between mb-4 px-1">
                      <h3 className="font-semibold text-sm uppercase tracking-wider">{column.title}</h3>
                      <Badge variant="secondary" className="bg-background">
                        {boardCards.filter(c => c.ui_status === column.id).length}
                      </Badge>
                    </div>

                    {/* Cards Container */}
                    <div className="flex-1 overflow-y-auto space-y-3 px-1 pb-2">
                       {boardCards
                        .filter(c => c.ui_status === column.id)
                        .map((card, index) => (
                          <Draggable key={card.id} draggableId={card.id} index={index}>
                            {(provided: any, snapshot: any) => (
                              <Card
                                ref={provided.innerRef}
                                {...provided.draggableProps}
                                {...provided.dragHandleProps}
                                className={`shadow-sm cursor-grab active:cursor-grabbing hover:border-primary/50 transition-colors ${snapshot.isDragging ? 'shadow-lg border-primary ring-1 ring-primary' : ''}`}
                              >
                                <CardContent className="p-4">
                                  <div className="flex justify-between items-start mb-2">
                                    <div className="font-semibold text-sm">{card.name}</div>
                                    <button className="text-muted-foreground hover:text-foreground">
                                      <MoreHorizontal className="w-4 h-4" />
                                    </button>
                                  </div>
                                  
                                  <div className="text-xs text-muted-foreground flex items-center gap-1 mb-3">
                                    <Building2 className="w-3 h-3" /> {card.company || "Unknown Company"}
                                  </div>

                                  {card.intent_score > 0 && (
                                    <div className="mb-3">
                                      <Badge variant="outline" className={`text-[10px] uppercase font-bold tracking-wider ${
                                         card.intent_score > 75 ? 'bg-green-500/10 text-green-600 border-green-500/20' : 
                                         card.intent_score > 40 ? 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20' : 'bg-slate-500/10 text-slate-600 border-slate-500/20'
                                      }`}>
                                        INTENT: {card.intent_score}/100
                                      </Badge>
                                    </div>
                                  )}

                                  <div className="text-[10px] text-muted-foreground bg-muted p-2 rounded line-clamp-2 border italic">
                                    "{card.buying_signal}"
                                  </div>

                                  <div className="mt-3 text-[10px] text-muted-foreground flex items-center gap-1 justify-end">
                                    <Clock className="w-3 h-3" /> {formatDistanceToNow(new Date(card.created_at))} ago
                                  </div>
                                </CardContent>
                              </Card>
                            )}
                          </Draggable>
                        ))}
                      {provided.placeholder}
                    </div>
                  </div>
                )}
              </Droppable>
            ))}
          </div>
        </DragDropContext>
      </div>
    </div>
  );
}

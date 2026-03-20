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
  MoreHorizontal,
  Mail,
  Wand2
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const ATS_COLUMNS = [
  { id: "sourced", title: "Sourced", color: "bg-slate-100 dark:bg-slate-900 border-slate-200" },
  { id: "outreached", title: "Outreach Sent", color: "bg-blue-50 dark:bg-blue-950 border-blue-200" },
  { id: "interviewing", title: "Interviewing", color: "bg-purple-50 dark:bg-purple-950 border-purple-200" },
  { id: "hired", title: "Hired", color: "bg-emerald-50 dark:bg-emerald-950 border-emerald-200" },
  { id: "rejected", title: "Rejected", color: "bg-red-50 dark:bg-red-950 border-red-200" },
];

async function fetchCandidates() {
  const token = localStorage.getItem("access_token");
  const res = await fetch("http://192.168.31.242:8000/api/v1/talent/candidates", {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to fetch candidates");
  const json = await res.json();
  return json.data;
}

async function updateCandidateStage(candidateId: string, stage: string) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`http://192.168.31.242:8000/api/v1/talent/candidates/${candidateId}/stage`, {
    method: "PUT",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}` 
    },
    body: JSON.stringify({ stage })
  });
  if (!res.ok) throw new Error("Failed to update status");
  return res.json();
}

export default function CandidateATSPage() {
  const queryClient = useQueryClient();
  const { data: rawCandidates = [], isLoading } = useQuery({
    queryKey: ["talent", "candidates", "ats"],
    queryFn: fetchCandidates
  });

  const [boardCards, setBoardCards] = useState<any[]>([]);

  useEffect(() => {
    if (rawCandidates.length > 0 && boardCards.length === 0) {
      setBoardCards(rawCandidates.map((p: any) => ({ ...p, ui_status: p.ats_status || "sourced" })));
    } else if (rawCandidates.length > boardCards.length) {
       const existingIds = new Set(boardCards.map(b => b.id));
       const newItems = rawCandidates.filter((p: any) => !existingIds.has(p.id)).map((p:any) => ({...p, ui_status: p.ats_status || "sourced"}));
       setBoardCards(prev => [...prev, ...newItems]);
    }
  }, [rawCandidates]);

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, stage }: { id: string, stage: string }) => updateCandidateStage(id, stage),
  });

  const onDragEnd = (result: any) => {
    const { destination, source, draggableId } = result;

    if (!destination) return;
    if (destination.droppableId === source.droppableId && destination.index === source.index) return;

    const newStage = destination.droppableId;
    
    // Optimistic Update
    setBoardCards(prevCards => 
      prevCards.map(card => 
        card.id === draggableId ? { ...card, ui_status: newStage } : card
      )
    );

    updateStatusMutation.mutate({ id: draggableId, stage: newStage });
  };

  if (isLoading) return <div className="p-8">Loading ATS Board...</div>;

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)]">
      <div className="mb-6 flex justify-between items-end p-6 pb-0">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Applicant Tracking Pipeline</h1>
          <p className="text-muted-foreground">Manage candidate lifecycles from Discovery to Hire.</p>
        </div>
      </div>

      <div className="flex-1 overflow-x-auto pb-4 p-6 pt-2">
        <DragDropContext onDragEnd={onDragEnd}>
          <div className="flex h-full gap-4 items-start min-w-[1200px]">
            {ATS_COLUMNS.map(column => (
              <Droppable key={column.id} droppableId={column.id}>
                {(provided: any, snapshot: any) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={`flex flex-col h-full w-[320px] rounded-xl border p-3 flex-shrink-0 transition-colors ${column.color} ${snapshot.isDraggingOver ? 'ring-2 ring-primary/50' : ''}`}
                  >
                    <div className="flex items-center justify-between mb-4 px-1">
                      <h3 className="font-semibold text-sm uppercase tracking-wider">{column.title}</h3>
                      <Badge variant="secondary" className="bg-background">
                        {boardCards.filter(c => c.ui_status === column.id).length}
                      </Badge>
                    </div>

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
                                    <Building2 className="w-3 h-3" /> {card.current_company || "Unknown Company"}
                                  </div>

                                  <div className="text-[10px] text-muted-foreground bg-muted p-2 rounded line-clamp-1 border mb-3">
                                    {card.current_role}
                                  </div>

                                  <div className="flex justify-between items-center mb-1">
                                    <Button variant="outline" size="sm" className="h-7 text-[10px] px-2" onClick={() => {}}>
                                      <Wand2 className="w-3 h-3 mr-1" /> Copilot Draft
                                    </Button>
                                    <Button size="sm" className="h-7 text-[10px] px-2 bg-blue-600 hover:bg-blue-700">
                                      <Mail className="w-3 h-3 mr-1" /> InMail
                                    </Button>
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

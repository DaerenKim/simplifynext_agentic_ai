import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Calendar as IconCalendar, MessageCircle, BarChart3, Settings, ExternalLink, RotateCcw } from "lucide-react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { GoogleCalendarView } from "./GoogleCalendarView";
import { SettingsModal } from "./SettingsModal";
// Removed typing queue imports - just show messages instantly

// -------------------- Types --------------------
interface OnboardingData {
  name: string;
  age: string;
  peaceActivities: string[];
  freeDayActivities: string[];
  goals: string[];
}
interface MainAppProps { userData: OnboardingData; }
interface ChatMessage { id: string; sender: "user" | "buddy"; message: string; timestamp: Date; }
type Proposal = { type: string; summary: string; start: string; end: string; reason?: string; };

// -------------------- Helpers --------------------
function wantsSchedulingIntent(s: string) {
  return /\b(plan|schedule|add|block|book|insert)\b/i.test(s);
}

// Helper to add a message
function createMessage(message: string, sender: "user" | "buddy" = "buddy"): ChatMessage {
  return {
    id: Date.now().toString(),
    sender,
    message,
    timestamp: new Date(),
  };
}
function bulletsFromProposals(ps: Proposal[]) {
  return ps.slice(0, 6)
    .map(p => `• ${p.summary} — ${new Date(p.start).toLocaleString([], { hour: "2-digit", minute: "2-digit" })} → ${new Date(p.end).toLocaleString([], { hour: "2-digit", minute: "2-digit" })}`)
    .join("\n");
}

// Helper function to group proposals by day
function groupProposalsByDay(proposals: any[]) {
  const grouped: {[key: string]: any[]} = {};
  
  proposals.forEach(proposal => {
    const date = new Date(proposal.start);
    const dayKey = date.toISOString().split('T')[0]; // YYYY-MM-DD format
    const dayLabel = date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      month: 'short', 
      day: 'numeric' 
    });
    
    if (!grouped[dayKey]) {
      grouped[dayKey] = [];
    }
    grouped[dayKey].push({...proposal, dayLabel});
  });
  
  return grouped;
}

// Helper function to format proposals for a single day
function formatDayProposals(dayProposals: any[]) {
  if (!dayProposals.length) return "";
  
  const dayLabel = dayProposals[0].dayLabel;
  const activities = dayProposals.map(p => {
    const startTime = new Date(p.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const endTime = new Date(p.end).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return `- ${p.summary} (${startTime}-${endTime})${p.reason ? ' - ' + p.reason : ''}`;
  }).join('\n');
  
  return `**${dayLabel}:**\n${activities}`;
}

// =================================================
//                    Component
// =================================================
export const MainApp = ({ userData }: MainAppProps) => {
  
  // ------------- Chat -------------
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      sender: "buddy",
      message: `Hi ${userData.name}! I'm your Unfrazzle Buddy. How can I support you today?`,
      timestamp: new Date(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState("");
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // ------------- OAuth / Calendar -------------
  const [isCalendarConnected, setIsCalendarConnected] = useState(false);
  const [activeEmail, setActiveEmail] = useState<string | null>(null);

  // ------------- Burnout Check-in (backend-driven) -------------
  const [burnoutScore, setBurnoutScore] = useState<number | null>(null); // 0..1
  const [needsInitialQuestions, setNeedsInitialQuestions] = useState(true);
  const [questionsAvailable, setQuestionsAvailable] = useState(true);
  const [isQuestionnaireOpen, setIsQuestionnaireOpen] = useState(false);
  const [cooldownUntil, setCooldownUntil] = useState<number | null>(null);
  const [questionnaireInProgress, setQuestionnaireInProgress] = useState(false);

  // ------------- Settings -------------
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  
  // ------------- Session -------------
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // ------------- Scheduler Consent -------------
  const [pendingProposals, setPendingProposals] = useState<Proposal[]>([]);
  const [awaitingConsent, setAwaitingConsent] = useState(false);
  const [currentDayProposals, setCurrentDayProposals] = useState<any[]>([]);
  const [currentDayIndex, setCurrentDayIndex] = useState(0);
  const [groupedProposals, setGroupedProposals] = useState<{[key: string]: any[]}>({});
  const [awaitingDayConsent, setAwaitingDayConsent] = useState(false);

  // ------------------------------------------------
  // Fresh start each load (optional but requested)
  // ------------------------------------------------
  useEffect(() => {
    fetch("/api/manager/reset", { method: "POST" }).catch(() => {});
  }, []);

  // ------------------------------------------------
  // OAuth helpers
  // ------------------------------------------------
  const handleGoogleCalendarAuth = () => {
    const popup = window.open("/oauth2/login", "google_oauth", "width=500,height=600,scrollbars=yes,resizable=yes");
    const checkClosed = setInterval(() => {
      if (popup?.closed) { clearInterval(checkClosed); checkAuthStatus(); }
    }, 800);
  };

  const checkAuthStatus = async () => {
    try {
      const res = await fetch("/oauth2/status");
      const data = await res.json();
      if (Array.isArray(data.authorized_emails) && data.authorized_emails.length > 0) {
        setIsCalendarConnected(true); setActiveEmail(data.authorized_emails[0]);
      } else if (data.authorized === true && data.email) {
        setIsCalendarConnected(true); setActiveEmail(data.email);
      } else { setIsCalendarConnected(false); setActiveEmail(null); }
    } catch { setIsCalendarConnected(false); setActiveEmail(null); }
  };

  // ------------------------------------------------
  // Burnout questionnaire (5 initial Qs, then cooldown)
  // ------------------------------------------------
  type NextQ = { qid: string; text: string };
  const [currentQ, setCurrentQ] = useState<NextQ | null>(null);
  const initialCountRef = useRef(0);

  const loadNextQuestion = async () => {
    const res = await fetch("/api/manager/checkin/next");
    if (!res.ok) throw new Error("Failed to fetch next question");
    const q = (await res.json()) as NextQ;
    setCurrentQ(q);
  };

  const answerQuestion = async (qid: string, value: number) => {
    const res = await fetch("/api/manager/checkin/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ qid, value }),
    });
    if (!res.ok) throw new Error("Failed to submit answer");
    const data = await res.json(); // { bs, next_interval_min }
    const bs = typeof data.bs === "number" ? data.bs : null;
    if (bs !== null) setBurnoutScore(bs);

    // cooldown handling
    const mins = Number(data.next_interval_min || 0);
    if (mins > 0) {
      const until = Date.now() + mins * 60_000;
      setCooldownUntil(until);
      setQuestionsAvailable(false);
      setTimeout(() => setQuestionsAvailable(true), mins * 60_000);
    }
    return data;
  };

  // load first Q when modal opens
  useEffect(() => {
    if (isQuestionnaireOpen) {
      initialCountRef.current = 0;
      setQuestionnaireInProgress(true);
      loadNextQuestion().catch(() => setCurrentQ(null));
    } else {
      setQuestionnaireInProgress(false);
    }
  }, [isQuestionnaireOpen]);

  const submitAnswer = async (value: number) => {
    if (!currentQ) return;
    try {
      const resp = await answerQuestion(currentQ.qid, value);
      initialCountRef.current += 1;
  
      if (initialCountRef.current < 5 && needsInitialQuestions) {
        await loadNextQuestion();
      } else {
        // Finished the initial 5
        setNeedsInitialQuestions(false);
        setIsQuestionnaireOpen(false);
        setQuestionsAvailable(false); // <== disable button immediately after finishing
        setQuestionnaireInProgress(false);
  
        // Thank user in chat
        setMessages(prev => [
          ...prev,
          createMessage(`Thanks for completing your check-in.`),
        ]);
  
        // Auto-plan like CLI: if not connected, ask to connect; else propose plan with consent
        if (!activeEmail) {
          setMessages(prev => [
            ...prev,
            createMessage("To suggest restorative activities, please connect your Google Calendar (middle panel)."),
          ]);
        } else {
          const plan = await planWithManager(3);
          if (plan.ok && plan.proposals && plan.proposals.length > 0) {
            // Show the detailed analysis if available
            if (plan.detailedAnalysis) {
              setMessages(prev => [
                ...prev,
                createMessage(plan.detailedAnalysis),
              ]);
            }
            
            // Start day-by-day approval
            startDayByDayApproval(plan.proposals, plan.sessionId);
            
          } else if (!plan.ok) {
            setMessages(prev => [
              ...prev,
              {
                id: (Date.now() + 2).toString(),
                sender: "buddy",
                message: plan.message ?? "Planner unavailable.",
                timestamp: new Date(),
              },
            ]);
          }
        }
      }
    } catch {
      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "buddy",
          message: "Hmm, I couldn't record that answer. Please try again.",
          timestamp: new Date(),
        },
      ]);
    }
  };

  // ------------------------------------------------
  // Scheduler: plan + consent + apply
  // ------------------------------------------------
  async function planWithManager(days = 3) {
    if (!activeEmail) return { ok: false, message: "Please connect Google Calendar first." };
    
    const res = await fetch("/api/manager/schedule/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        email: activeEmail, 
        user: userData.name, 
        days 
      }),
    });
    
    if (res.status === 401) return { ok: false, message: "Authorization required. Connect Google Calendar first." };
    if (!res.ok) return { ok: false, message: `Planner error: ${await res.text()}` };
    
    const data = await res.json();
    
    if (data.finished && !data.session_id) {
      return { 
        ok: false, 
        message: data.message || "No suggestions at this time.",
        rawText: data.raw_text 
      };
    }
    
    // Extract all proposals and analysis
    let allProposals = [];
    let detailedAnalysis = "";
    
    if (data.raw_text) {
      // Extract the analysis part (everything before <response>)
      const analysisMatch = data.raw_text.match(/^(.*?)(?=<response>)/s);
      if (analysisMatch) {
        detailedAnalysis = analysisMatch[1].trim();
      }
      
      // Extract the payload for actual proposals
      const payloadMatch = data.raw_text.match(/<payload>\s*(\{.*?\})\s*<\/payload>/s);
      if (payloadMatch) {
        try {
          const payload = JSON.parse(payloadMatch[1]);
          allProposals = payload.proposals || [];
        } catch (e) {
          console.error("Failed to parse payload:", e);
        }
      }
    }
    
    return { 
      ok: true, 
      proposals: allProposals,
      sessionId: data.session_id,
      detailedAnalysis: detailedAnalysis,
      text: data.raw_text || "" 
    };
  }

  // function to start day-by-day approval process
  function startDayByDayApproval(proposals: any[], sessionId: string) {
    const grouped = groupProposalsByDay(proposals);
    const dayKeys = Object.keys(grouped).sort(); // Sort by date
    
    setGroupedProposals(grouped);
    setCurrentDayIndex(0);
    setCurrentSessionId(sessionId);
    
    if (dayKeys.length > 0) {
      const firstDay = grouped[dayKeys[0]];
      setCurrentDayProposals(firstDay);
      setAwaitingDayConsent(true);
      
      // Show the first day's proposals
      const dayMessage = formatDayProposals(firstDay);
      setMessages(prev => [...prev, createMessage(`${dayMessage}\n\nApprove activities for this day? (yes/no)`)]);
    }
  }
  
  
  async function applyProposalsWithManager(sessionId: string, proposals: any[]) {
    if (!sessionId) {
      // Fallback to direct scheduler apply if no session
      return applyProposalsDirect(proposals);
    }
    
    let accepted = [];
    
    // Go through each proposal in the session
    for (let i = 0; i < proposals.length; i++) {
      const proposal = proposals[i];
      
      // For now, auto-accept all (you can add UI logic here later)
      const decision = true; // In real UI, this would come from user interaction
      
      const res = await fetch("/api/manager/schedule/decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          session_id: sessionId, 
          accept: decision 
        }),
      });
      
      if (!res.ok) {
        console.error("Failed to process proposal decision");
        break;
      }
      
      const result = await res.json();
      if (result.result?.status === "scheduled") {
        accepted.push(proposal.summary);
      }
      
      // Break if session is finished
      if (result.finished) break;
    }
    
    return { ok: true, added: accepted, count: accepted.length };
  }
  
  // Keep the original as fallback
  async function applyProposalsDirect(proposals: any[]) {
    if (!activeEmail) return { ok: false, message: "No authorized calendar email." };
    const res = await fetch("/api/scheduler/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: activeEmail, proposals }),
    });
    if (!res.ok) return { ok: false, message: `Apply error: ${await res.text()}` };
    const data = await res.json();
    return { ok: true, ...data };
  }

// New function to handle day approval
async function handleDayApproval(approve: boolean) {
  const dayKeys = Object.keys(groupedProposals).sort();
  let acceptedCount = 0;
  
  if (approve && currentDayProposals.length > 0) {
    // Apply all proposals for this day
    for (const proposal of currentDayProposals) {
      try {
        const res = await fetch("/api/manager/schedule/decision", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            session_id: currentSessionId, 
            accept: true  // ✅ CORRECT: When user approves, we accept in the API
          }),
        });
        
        if (res.ok) {
          const result = await res.json();
          if (result.result?.status === "scheduled") {
            acceptedCount++;
          }
        }
      } catch (error) {
        console.error("Failed to schedule proposal:", error);
      }
    }
    
    setMessages(prev => [...prev, {
      id: (Date.now() + 1).toString(),
      sender: "buddy",
      message: `Added ${acceptedCount} activities for ${currentDayProposals[0]?.dayLabel} ✅`,
      timestamp: new Date(),
    }]);
  } else {
    // User said "no" - we need to reject each proposal in the session
    for (const proposal of currentDayProposals) {
      try {
        const res = await fetch("/api/manager/schedule/decision", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            session_id: currentSessionId, 
            accept: false  // ✅ CORRECT: When user rejects, we reject in the API
          }),
        });
        
        // We don't need to check the result for rejections
      } catch (error) {
        console.error("Failed to reject proposal:", error);
      }
    }
    
    setMessages(prev => [...prev, {
      id: (Date.now() + 1).toString(),
      sender: "buddy",
      message: `Skipped activities for ${currentDayProposals[0]?.dayLabel}`,
      timestamp: new Date(),
    }]);
  }
  
  // Move to next day
  const nextDayIndex = currentDayIndex + 1;
  if (nextDayIndex < dayKeys.length) {
    setCurrentDayIndex(nextDayIndex);
    const nextDay = groupedProposals[dayKeys[nextDayIndex]];
    setCurrentDayProposals(nextDay);
    
    setTimeout(() => {
      const dayMessage = formatDayProposals(nextDay);
      setMessages(prev => [...prev, {
        id: (Date.now() + 2).toString(),
        sender: "buddy",
        message: `${dayMessage}\n\nApprove activities for this day? (yes/no)`,
        timestamp: new Date(),
      }]);
    }, 1000);
  } else {
    // Finished all days
    setAwaitingDayConsent(false);
    setCurrentSessionId(null);
    setGroupedProposals({});
    setCurrentDayProposals([]);
    setCurrentDayIndex(0);
    
    setMessages(prev => [...prev, {
      id: (Date.now() + 3).toString(),
      sender: "buddy",
      message: "Finished reviewing all days! Let me know if you need anything else.",
      timestamp: new Date(),
    }]);
  }
}

  // ------------------------------------------------
  // Chat handler (manager-driven)
  // ------------------------------------------------
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;
    const userText = inputMessage.trim();
  
    setMessages(prev => [...prev, { id: Date.now().toString(), sender: "user", message: userText, timestamp: new Date() }]);
    setInputMessage("");
  
    // 1) Waiting for day-by-day consent?
    if (awaitingDayConsent) {
      const s = userText.toLowerCase();
      if (/^(y|yes|approve|ok|okay|sure)$/.test(s)) {
        await handleDayApproval(true);
      } else if (/^(n|no|cancel|skip)$/.test(s)) {
        await handleDayApproval(false);
      } else {
        setMessages(prev => [...prev, { 
          id: (Date.now() + 1).toString(), 
          sender: "buddy", 
          message: "Please reply with **yes** or **no** for this day's activities.", 
          timestamp: new Date() 
        }]);
      }
      return; // Exit early when handling day consent
    }
  
    // 2) Waiting for old-style all-at-once consent?
    if (awaitingConsent) {
      const s = userText.toLowerCase();
      if (/^(y|yes|approve|ok|okay|sure)$/.test(s)) {
        const res = await applyProposalsWithManager(currentSessionId, pendingProposals);
        if (res.ok) {
          setMessages(prev => [...prev, { 
            id: (Date.now() + 1).toString(), 
            sender: "buddy", 
            message: `Added ${res.count} item(s) to your Google Calendar ✅`, 
            timestamp: new Date() 
          }]);
        } else {
          setMessages(prev => [...prev, { 
            id: (Date.now() + 1).toString(), 
            sender: "buddy", 
            message: res.message || "Something went wrong while applying the plan.", 
            timestamp: new Date() 
          }]);
        }
        setPendingProposals([]); 
        setCurrentSessionId(null);
        setAwaitingConsent(false);
      } else if (/^(n|no|cancel|skip)$/.test(s)) {
        setMessages(prev => [...prev, { 
          id: (Date.now() + 1).toString(), 
          sender: "buddy", 
          message: "No problem—nothing was added. Tell me if you want to plan again.", 
          timestamp: new Date() 
        }]);
        setPendingProposals([]); 
        setCurrentSessionId(null);
        setAwaitingConsent(false);
      } else {
        setMessages(prev => [...prev, { 
          id: (Date.now() + 1).toString(), 
          sender: "buddy", 
          message: "Please reply with **yes** or **no**.", 
          timestamp: new Date() 
        }]);
      }
      return; // Exit early when handling consent
    }
  
    // 3) If user asked to schedule/plan, trigger planner
    if (wantsSchedulingIntent(userText)) {
      const plan = await planWithManager(3);
      if (plan.ok && plan.proposals && plan.proposals.length > 0) {
        // First, show the detailed analysis if available
        if (plan.detailedAnalysis) {
          setMessages(prev => [
            ...prev,
            {
              id: (Date.now() + 1).toString(),
              sender: "buddy",
              message: plan.detailedAnalysis,
              timestamp: new Date(),
            },
          ]);
        }
        
        // Start day-by-day approval process after a delay
        setTimeout(() => {
          startDayByDayApproval(plan.proposals, plan.sessionId);
        }, 2000);
        
      } else if (!plan.ok) {
        setMessages(prev => [...prev, { 
          id: (Date.now() + 2).toString(), 
          sender: "buddy", 
          message: plan.message ?? "Planner unavailable.", 
          timestamp: new Date() 
        }]);
      }
      return; // Exit early after handling scheduling
    }
  
    // 4) Always ask Manager's Advisor path (only if not handling consent or scheduling)
    try {
      const resp = await fetch("/api/manager/support", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user: userData.name, message: userText }),
      });
      const data = await resp.json();
      setMessages(prev => [...prev, createMessage(data.text || "I understand. How can I help further?")]);
    } catch {
      setMessages(prev => [...prev, createMessage("I'm having trouble connecting right now. Please try again in a moment.")]);
    }
  };

  // -------------------- UI helpers --------------------
  const checkinCTASecondaryText = useMemo(() => {
    if (needsInitialQuestions) return "Complete initial questions";
    if (!questionsAvailable) {
      const minsLeft = cooldownUntil ? Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 60_000)) : 0;
      return `Next check in ~${minsLeft} min`;
    }
    return "New questions available";
  }, [needsInitialQuestions, questionsAvailable, cooldownUntil]);

  const checkinDisabled = !questionsAvailable;

  // Sequential flashing logic
  const shouldFlashCalendar = !isCalendarConnected;
  const shouldFlashQuestionnaire = isCalendarConnected && questionsAvailable && !questionnaireInProgress && !checkinDisabled;

  // Auto-scroll chat to bottom when new messages arrive or during typing
  useEffect(() => {
    const scrollToBottom = () => {
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
      }
    };

    scrollToBottom();
  }, [messages]);

  // =================================================
  //                     Render
  // =================================================
  return (
    <div className="h-screen bg-background text-foreground relative">
      <PanelGroup direction="horizontal">
        {/* LEFT */}
        <Panel defaultSize={25} minSize={20} maxSize={40}>
          <div className="h-full bg-card border-r border-border p-6 flex flex-col overflow-hidden">
            <div className="mb-8">
              <h2 className="text-xl font-medium mb-2 truncate">Welcome back, {userData.name}</h2>
              <p className="text-sm text-muted-foreground break-words">
                Let's work towards your goals: {userData.goals.slice(0, 2).join(", ") || "—"}
              </p>
            </div>

            <div className="space-y-4 flex-1 overflow-y-auto">
              <Button
                variant={checkinDisabled ? "outline" : "default"}
                disabled={checkinDisabled}
                className={`w-full justify-start gap-3 p-4 h-auto min-h-0 transition-all duration-1000 ${
                  shouldFlashQuestionnaire ? "animate-[pulse_6s_ease-in-out_infinite] shadow-md" : ""
                } ${checkinDisabled ? "opacity-50 cursor-not-allowed pointer-events-none" : ""}`}
                onClick={() => { if (!checkinDisabled) setIsQuestionnaireOpen(true); }}
              >
                <BarChart3 className="w-5 h-5 text-primary flex-shrink-0" />
                <div className="text-left min-w-0 flex-1">
                  <div className="font-medium truncate">
                    {needsInitialQuestions ? "Start Assessment" : "Burnout Check-in"}
                  </div>
                  <div className="text-sm text-muted-foreground truncate">{checkinCTASecondaryText}</div>
                </div>
              </Button>

              <Button
                variant="outline"
                className="w-full justify-start gap-3 p-4 h-auto min-h-0"
                onClick={() => setIsSettingsOpen(true)}
              >
                <Settings className="w-5 h-5 text-primary flex-shrink-0" />
                <div className="text-left min-w-0 flex-1">
                  <div className="font-medium truncate">Settings</div>
                  <div className="text-sm text-muted-foreground truncate">Customize your experience</div>
                </div>
              </Button>
            </div>

            <div className="mt-auto pt-4 border-t border-border overflow-hidden">
              <div className="text-xs text-muted-foreground mb-3 truncate">Your Unfrazzle Goals</div>
              <div className="space-y-2">
                <div className="min-w-0">
                  <span className="text-xs font-medium">Primary: </span>
                  <span className="text-xs text-muted-foreground break-words">{userData.goals.length > 0 ? userData.goals.join(", ") : "Not set"}</span>
                </div>
                <div className="min-w-0">
                  <span className="text-xs font-medium">Peace Activity: </span>
                  <span className="text-xs text-muted-foreground break-words">{userData.peaceActivities.length > 0 ? userData.peaceActivities.join(", ") : "Not set"}</span>
                </div>
                <div className="min-w-0">
                  <span className="text-xs font-medium">Free Day Choice: </span>
                  <span className="text-xs text-muted-foreground break-words">{userData.freeDayActivities.length > 0 ? userData.freeDayActivities.join(", ") : "Not set"}</span>
                </div>
              </div>
            </div>
          </div>
        </Panel>

        <PanelResizeHandle className="w-1 bg-border hover:bg-primary/50 transition-colors" />

        {/* MIDDLE — Calendar */}
        <Panel defaultSize={50} minSize={30}>
          <div className="h-full p-6 flex flex-col bg-gradient-calm animate-gradient relative">
            <div className="mb-6 relative z-10">
              <h3 className="text-lg font-medium mb-4 text-white">Your Calendar</h3>
              {!isCalendarConnected ? (
                <Card className="border-dashed border-2 border-muted">
                  <CardContent className="flex flex-col items-center justify-center py-12">
                    <IconCalendar className="w-12 h-12 text-muted-foreground mb-4" />
                    <h4 className="text-lg font-medium mb-2">Connect Your Google Calendar</h4>
                    <p className="text-muted-foreground text-center mb-6 max-w-md">
                      Connect your Google Calendar to help us understand your schedule and suggest better work-life balance.
                    </p>
                     <Button 
                       onClick={handleGoogleCalendarAuth} 
                       className={`gap-2 transition-all duration-1000 ${
                         shouldFlashCalendar ? "animate-[pulse_6s_ease-in-out_infinite] shadow-md" : ""
                       }`}
                     >
                       <ExternalLink className="w-4 h-4" />
                       Sign in to Google to connect your Calendar
                     </Button>
                  </CardContent>
                </Card>
              ) : (
                <GoogleCalendarView isConnected={isCalendarConnected} />
              )}
            </div>
          </div>
        </Panel>

        <PanelResizeHandle className="w-1 bg-border hover:bg-primary/50 transition-colors" />

        {/* RIGHT — Chat */}
        <Panel defaultSize={25} minSize={20} maxSize={40}>
          <div className="h-full bg-card border-l border-border flex flex-col">
            <div className="p-6 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
                    <MessageCircle className="w-5 h-5 text-primary-foreground" />
                  </div>
                  <div>
                    <h3 className="font-medium">Unfrazzle Buddy</h3>
                    <p className="text-sm text-muted-foreground">Your mindful companion</p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setMessages([
                      {
                        id: "1",
                        sender: "buddy",
                        message: `Hi ${userData.name}! I'm your Unfrazzle Buddy. How can I support you today?`,
                        timestamp: new Date(),
                      },
                    ]);
                    setInputMessage("");
                    setPendingProposals([]);
                    setAwaitingConsent(false);
                  }}
                  className="h-8 w-8 p-0"
                  title="Reset conversation"
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <ScrollArea className="flex-1 p-6" ref={scrollContainerRef}>
              <div className="space-y-4">
                {messages.map((m) => (
                  <div key={m.id} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] p-3 rounded-lg ${m.sender === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"}`}>
                      <p className="text-sm whitespace-pre-wrap">
                        {m.message}
                      </p>
                      <p className="text-xs opacity-70 mt-1">
                        {m.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>

            <div className="p-6 border-t border-border">
              <div className="flex gap-2">
                <Input
                  placeholder="Type your message..."
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                  className="flex-1"
                />
                <Button onClick={handleSendMessage} disabled={!inputMessage.trim()}>
                  Send
                </Button>
              </div>
            </div>
          </div>
        </Panel>
      </PanelGroup>

      {/* Burnout Questionnaire Modal (inline) */}
      {isQuestionnaireOpen && (
        <div className="absolute inset-0 bg-black/40 z-40 flex items-center justify-center">
          <div className="bg-card rounded-xl border border-border w-full max-w-md p-6 shadow-xl">
            <h4 className="text-lg font-medium mb-3">Quick check-in</h4>
            <p className="text-sm text-muted-foreground mb-4">
              {currentQ ? currentQ.text : "Loading..."}
            </p>

            <div className="grid grid-cols-5 gap-2 mb-4">
              {[1, 2, 3, 4, 5].map((v) => (
                <Button key={v} variant="outline" onClick={() => submitAnswer(v)}>
                  {v}
                </Button>
              ))}
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setIsQuestionnaireOpen(false)}>Close</Button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
};

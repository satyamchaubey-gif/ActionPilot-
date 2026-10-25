import { useEffect, useMemo, useState, useRef } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronDown,
  Clock3,
  Clock,
  FileText,
  Filter,
  History,
  Inbox,
  LayoutDashboard,
  ListTodo,
  LoaderCircle,
  Plus,
  Search,
  ShieldCheck,
  Shield,
  Sparkles,
  UploadCloud,
  Workflow,
  X,
  Send,
  RefreshCw,
  LogOut,
  Mail,
  Lock,
  User as UserIcon,
  Mic,
  MicOff,
  Calendar,
  Slack,
  Github,
  ExternalLink,
  Zap,
  CheckCircle2,
  Radio,
  Sun,
  Moon,
  Menu,
  Settings,
  Users,
  Phone,
  Briefcase,
  Copy,
  Trash2,
  Volume2,
} from "lucide-react";

const API = import.meta.env.VITE_API_BASE_URL ?? "";

function formatApiError(err: any): string {
  const msg = err?.message || String(err || "");
  if (msg === "Failed to fetch") {
    return "Cannot connect to backend server. If using Render free tier, the server may be waking up from sleep (~50s delay). Please wait 30 seconds and try again.";
  }
  if (msg.includes("Unexpected token '<'") || msg.includes("is not valid JSON")) {
    return "Backend connection error: Received HTML instead of JSON. Ensure 'VITE_API_BASE_URL' in Vercel is set to your Render backend URL (e.g. https://your-app.onrender.com).";
  }
  return msg || "An unexpected error occurred.";
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return "Good morning";
  if (hour >= 12 && hour < 17) return "Good afternoon";
  if (hour >= 17 && hour < 23) return "Good evening";
  return "Welcome back";
}

type User = {
  id: string;
  email: string;
  full_name: string;
  contact_no?: string;
  age?: number | null;
  job_title?: string;
  preferences?: Record<string, any>;
  is_verified: boolean;
  created_at: string;
};

type Meeting = {
  id: string;
  title: string;
  recorded_at: string;
  duration_seconds: number;
  transcript: string;
  speakers: string[];
  task_count: number;
  created_at: string;
};

type SpeakerTurn = {
  id: string;
  speaker: string;
  text: string;
  timestamp: string;
};

type Ev = { quote: string; start: number; end: number; source_name: string };
type Task = {
  id: string;
  document_id: string;
  title: string;
  description: string;
  assignee?: string | null;
  due_date?: string | null;
  priority: string;
  dependencies: string[];
  evidence: Ev[];
  confidence: number;
  uncertainty_flags: string[];
  status: string;
  draft?: string | null;
  dispatched?: number;
  dispatched_at?: string | null;
  dispatch_channel?: string | null;
  created_at: string;
};
type Doc = {
  id: string;
  title: string;
  filename?: string | null;
  created_at: string;
  status: string;
  task_count: number;
};
type Audit = {
  id: number;
  entity_type: string;
  entity_id: string;
  event_type: string;
  actor: string;
  details: any;
  created_at: string;
};

const dateLabel = (s?: string | null) =>
  s ? new Date(s + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "No due date";
const timeLabel = (s: string) =>
  new Date(s).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

function Badge({ children, tone = "" }: { children: any; tone?: string }) {
  return <span className={"badge " + tone}>{children}</span>;
}

export default function App() {
  // Theme State (Dark / Light)
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const saved = localStorage.getItem("actionpilot_theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("actionpilot_theme", theme);
  }, [theme]);

  function toggleTheme() {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }

  // Mobile Navigation Drawer State
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Authentication State
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("actionpilot_token"));
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authChecking, setAuthChecking] = useState<boolean>(true);
  const [authMode, setAuthMode] = useState<"login" | "signup" | "verify">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authFullName, setAuthFullName] = useState("");
  const [authCode, setAuthCode] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authNotice, setAuthNotice] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);

  // Workspace Data State
  const [docs, setDocs] = useState<Doc[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [audit, setAudit] = useState<Audit[]>([]);
  const [active, setActive] = useState("overview");
  const [selected, setSelected] = useState<Task | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [uploadText, setUploadText] = useState("");
  const [uploadTitle, setUploadTitle] = useState("Meeting notes");
  const [showIngest, setShowIngest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState("checking");
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");
  const [draft, setDraft] = useState({ channel: "email", recipient: "", subject: "", body: "" });
  const [draftOpen, setDraftOpen] = useState(false);
  const [edit, setEdit] = useState({ title: "", assignee: "", due_date: "", priority: "medium", description: "" });
  const [auditFilter, setAuditFilter] = useState("");

  // ================= Top-5 Hackathon Features States =================
  // Feature 1: Live Voice Note Recording & Voice Intelligence Studio
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [recognitionInstance, setRecognitionInstance] = useState<any>(null);
  const [voiceStudioOpen, setVoiceStudioOpen] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [voiceWordsCount, setVoiceWordsCount] = useState(0);

  const transcriptRef = useRef("");
  const recognitionRef = useRef<any>(null);
  const initialUploadTextRef = useRef("");
  const isExplicitlyRecordingRef = useRef(false);
  const accumulatedTranscriptRef = useRef("");
  const audioContextRef = useRef<any>(null);
  const analyserRef = useRef<any>(null);
  const mediaStreamRef = useRef<any>(null);
  const animFrameRef = useRef<any>(null);

  // Feature 2: 1-Click Demo Presets
  const [showDemoMenu, setShowDemoMenu] = useState(false);

  // Feature 3: Interactive Side-by-Side Evidence Highlighting
  const [sourceDocText, setSourceDocText] = useState<{ title: string; content: string } | null>(null);
  const [sourceInspectorOpen, setSourceInspectorOpen] = useState(false);
  const [targetHighlight, setTargetHighlight] = useState<string>("");

  // Feature 4: AI Conflict Resolver
  const [conflictModalTask, setConflictModalTask] = useState<Task | null>(null);

  // Feature 5: One-Click Action Dispatcher
  const [dispatchModalOpen, setDispatchModalOpen] = useState(false);
  const [dispatchTask, setDispatchTask] = useState<Task | null>(null);
  const [dispatchChannel, setDispatchChannel] = useState<"calendar" | "slack" | "github" | "email">("calendar");
  const [dispatchTarget, setDispatchTarget] = useState("");
  const [dispatchSimulate, setDispatchSimulate] = useState(true);
  const [dispatchFeedback, setDispatchFeedback] = useState<any>(null);
  const [dispatchLoading, setDispatchLoading] = useState(false);

  // Feature 6: Meeting History & Notes Archive
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [activeMeetingModal, setActiveMeetingModal] = useState<Meeting | null>(null);
  const [meetingSearch, setMeetingSearch] = useState("");

  // Feature 7: Multi-Speaker Diarization & Room Voice Mode
  const [multiSpeakerMode, setMultiSpeakerMode] = useState(true);
  const [activeSpeaker, setActiveSpeaker] = useState("Speaker 1 (Lead)");
  const [availableSpeakers, setAvailableSpeakers] = useState<string[]>([
    "Speaker 1 (Lead)",
    "Speaker 2 (Alex)",
    "Speaker 3 (Sam)",
    "Speaker 4 (Priya)",
  ]);
  const [speakerTurns, setSpeakerTurns] = useState<SpeakerTurn[]>([]);
  const activeSpeakerRef = useRef("Speaker 1 (Lead)");

  // Feature 8: User Profile & Customization Settings
  const [profileName, setProfileName] = useState("");
  const [profileEmail, setProfileEmail] = useState("");
  const [profilePhone, setProfilePhone] = useState("");
  const [profileAge, setProfileAge] = useState<number | "">("");
  const [profileJobTitle, setProfileJobTitle] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileNotice, setProfileNotice] = useState("");
  const [profileError, setProfileError] = useState("");
  const [appCustomization, setAppCustomization] = useState({
    roomSensitivity: "high",
    autoPunctuate: true,
    highFidelityMode: true,
  });

  // Authenticated API request helper
  async function req(path: string, init?: RequestInit) {
    const headers: Record<string, string> = {
      ...((init?.headers as Record<string, string>) || {}),
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    let r: Response;
    try {
      r = await fetch(API + path, { ...init, headers });
    } catch (e: any) {
      throw Error(formatApiError(e));
    }
    if (r.status === 401) {
      setToken(null);
      setCurrentUser(null);
      localStorage.removeItem("actionpilot_token");
      throw Error("Session expired. Please sign in again.");
    }
    if (!r.ok) {
      let m = `Request failed (${r.status})`;
      try {
        const body = await r.json();
        m = body.detail || m;
      } catch {}
      throw Error(m);
    }
    try {
      return await r.json();
    } catch (e: any) {
      throw Error(formatApiError(e));
    }
  }

  // Validate existing token on load
  useEffect(() => {
    async function verifyAuth() {
      if (!token) {
        setAuthChecking(false);
        return;
      }
      try {
        const me = await req("/api/auth/me");
        setCurrentUser(me);
      } catch {
        setToken(null);
        setCurrentUser(null);
        localStorage.removeItem("actionpilot_token");
      } finally {
        setAuthChecking(false);
      }
    }
    verifyAuth();
  }, [token]);

  // Sync currentUser attributes to profile form state
  useEffect(() => {
    if (currentUser) {
      setProfileName(currentUser.full_name || "");
      setProfileEmail(currentUser.email || "");
      setProfilePhone(currentUser.contact_no || "");
      setProfileAge(currentUser.age != null ? currentUser.age : "");
      setProfileJobTitle(currentUser.job_title || "");
      if (currentUser.preferences) {
        setAppCustomization((prev) => ({ ...prev, ...currentUser.preferences }));
      }
    }
  }, [currentUser]);

  // Load workspace data when authenticated
  async function refresh() {
    if (!token || !currentUser) return;
    try {
      const [d, t, a, h, m] = await Promise.all([
        req("/api/documents"),
        req("/api/tasks"),
        req("/api/audit?limit=100"),
        req("/api/health"),
        req("/api/meetings").catch(() => []),
      ]);
      setDocs(d);
      setTasks(t);
      setAudit(a);
      setHealth(h.status);
      setMeetings(m || []);
      setError("");
    } catch (e: any) {
      setHealth("offline");
      setError(e.message || "Cannot connect to API");
    }
  }

  useEffect(() => {
    if (currentUser && token) {
      refresh();
      const interval = setInterval(refresh, 12000);
      return () => clearInterval(interval);
    }
  }, [currentUser, token]);

  // Voice recording timer
  useEffect(() => {
    let interval: any;
    if (isRecording) {
      interval = setInterval(() => setRecordingSeconds((s) => s + 1), 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  function notify(s: string) {
    setToast(s);
    setTimeout(() => setToast(""), 3500);
  }

  // Workspace text analysis helper
  async function executeIngest(customTitle?: string, customText?: string) {
    const textToIngest = (customText !== undefined ? customText : uploadText).trim();
    const titleToIngest = (customTitle !== undefined ? customTitle : uploadTitle).trim() || "Meeting notes";
    if (!textToIngest) return;
    setLoading(true);
    try {
      const r = await req("/api/documents/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: titleToIngest, text: textToIngest }),
      });
      await refresh();
      setShowIngest(false);
      setUploadText("");
      setActive("tasks");
      notify(r.duplicate ? "Duplicate note detected — existing tasks displayed in workspace." : "🎙️ Voice memo analyzed and evidence-linked tasks extracted!");
    } catch (e: any) {
      setError(e.message || "Failed to analyze document");
    } finally {
      setLoading(false);
    }
  }

  // Feature 1: Live Voice Recording Handlers & Multi-Speaker Voice Studio
  function handleSelectSpeaker(spk: string) {
    setActiveSpeaker(spk);
    activeSpeakerRef.current = spk;
  }

  function handleAddSpeaker() {
    const nextNum = availableSpeakers.length + 1;
    const name = prompt("Enter speaker name:", `Speaker ${nextNum}`);
    if (name && name.trim()) {
      const clean = name.trim();
      if (!availableSpeakers.includes(clean)) {
        setAvailableSpeakers((prev) => [...prev, clean]);
      }
      setActiveSpeaker(clean);
      activeSpeakerRef.current = clean;
    }
  }

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setProfileSaving(true);
    setProfileNotice("");
    setProfileError("");
    try {
      const payload: any = {
        full_name: profileName,
        email: profileEmail,
        contact_no: profilePhone,
        age: profileAge === "" ? null : Number(profileAge),
        job_title: profileJobTitle,
        preferences: appCustomization,
      };
      const res = await req("/api/auth/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.user) {
        setCurrentUser(res.user);
      }
      if (res.token) {
        setToken(res.token);
        localStorage.setItem("actionpilot_token", res.token);
      }
      setProfileNotice("Profile details and preferences saved successfully!");
      notify("Profile updated successfully");
      setTimeout(() => setProfileNotice(""), 4000);
    } catch (err: any) {
      setProfileError(err.message || "Failed to update profile");
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleDeleteMeeting(id: string) {
    if (!confirm("Are you sure you want to remove this meeting recording from history?")) return;
    try {
      await req(`/api/meetings/${id}`, { method: "DELETE" });
      setMeetings((prev) => prev.filter((m) => m.id !== id));
      if (activeMeetingModal?.id === id) {
        setActiveMeetingModal(null);
      }
      notify("Meeting removed from history.");
    } catch (err: any) {
      notify("Failed to delete meeting: " + err.message);
    }
  }

  function startVoiceRecording() {
    setVoiceStudioOpen(true);
    isExplicitlyRecordingRef.current = true;
    accumulatedTranscriptRef.current = "";
    transcriptRef.current = "";
    setVoiceTranscript("");
    setVoiceWordsCount(0);
    setRecordingSeconds(0);
    setIsRecording(true);

    // 1. Omnidirectional High-Sensitivity Conference Audio Capture
    // Disabling aggressive noise cancellation so room voices aren't filtered as background noise
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices
        .getUserMedia({
          audio: {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: true,
            channelCount: 2,
          },
        })
        .then((stream) => {
          mediaStreamRef.current = stream;
          const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
          if (AudioContextClass) {
            const ctx = new AudioContextClass();
            audioContextRef.current = ctx;
            const src = ctx.createMediaStreamSource(stream);
            const analyser = ctx.createAnalyser();
            analyser.fftSize = 64;
            src.connect(analyser);
            analyserRef.current = analyser;
            const data = new Uint8Array(analyser.frequencyBinCount);
            const pollAudio = () => {
              if (!isExplicitlyRecordingRef.current) return;
              analyser.getByteFrequencyData(data);
              let sum = 0;
              for (let i = 0; i < data.length; i++) sum += data[i];
              const level = Math.min(100, Math.round((sum / data.length) * 1.8));
              setAudioLevel(level);
              animFrameRef.current = requestAnimationFrame(pollAudio);
            };
            pollAudio();
          }
        })
        .catch((err) => {
          console.warn("Audio meter init warning:", err);
        });
    }

    // 2. Start Continuous Keep-Alive Speech Recognition with Speaker Tracking
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      notify("Web Speech API not detected in this browser — Voice Studio loaded in interactive demo mode!");
      return;
    }

    function createRecognizer() {
      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "en-US";

      rec.onresult = (event: any) => {
        let currentSessionText = "";
        for (let i = 0; i < event.results.length; ++i) {
          currentSessionText += event.results[i][0].transcript + " ";
        }
        const full = (accumulatedTranscriptRef.current + " " + currentSessionText).trim();
        transcriptRef.current = full;
        setVoiceTranscript(full);
        setVoiceWordsCount(full.split(/\s+/).filter(Boolean).length);
        setUploadText(full);

        // Record finalized phrases under active speaker
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            const phrase = event.results[i][0].transcript.trim();
            if (phrase) {
              const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
              setSpeakerTurns((prev) => [
                ...prev,
                {
                  id: Math.random().toString(36).substring(2, 9),
                  speaker: activeSpeakerRef.current || activeSpeaker,
                  text: phrase,
                  timestamp: timeStr,
                },
              ]);
            }
          }
        }
      };

      rec.onerror = (e: any) => {
        console.warn("Speech recognition warning:", e.error);
        if (e.error === "not-allowed" || e.error === "service-not-allowed") {
          isExplicitlyRecordingRef.current = false;
          setIsRecording(false);
          notify("Microphone permission denied. Please allow microphone in browser settings.");
        }
      };

      rec.onend = () => {
        // Continuous Keep-Alive: If user hasn't clicked stop, auto-restart seamlessly!
        if (isExplicitlyRecordingRef.current) {
          accumulatedTranscriptRef.current = transcriptRef.current;
          try {
            const nextRec = createRecognizer();
            if (nextRec) {
              recognitionRef.current = nextRec;
              setRecognitionInstance(nextRec);
              nextRec.start();
            }
          } catch (err) {
            console.warn("Keep-alive auto-restart failed:", err);
          }
        } else {
          setIsRecording(false);
        }
      };

      return rec;
    }

    try {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch {}
      }
      const recognizer = createRecognizer();
      if (recognizer) {
        recognitionRef.current = recognizer;
        setRecognitionInstance(recognizer);
        recognizer.start();
        notify("🎙️ Voice Studio is listening in Multi-Voice Room Mode... Speak naturally.");
      }
    } catch (err: any) {
      console.warn("Recognizer start failed:", err);
      notify("Could not initialize microphone. Please check browser permissions.");
    }
  }

  function stopVoiceRecording(autoExtract: boolean = false) {
    isExplicitlyRecordingRef.current = false;
    setIsRecording(false);

    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
    }
    if (mediaStreamRef.current) {
      try { mediaStreamRef.current.getTracks().forEach((track: any) => track.stop()); } catch {}
    }
    if (audioContextRef.current) {
      try { audioContextRef.current.close(); } catch {}
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
    }
    setAudioLevel(0);

    const captured = (transcriptRef.current || voiceTranscript).trim();
    if (captured) {
      const autoTitle = "Meeting Recording (" + new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + ")";
      setUploadTitle((prev) => (!prev || prev === "Meeting notes") ? autoTitle : prev);
      setUploadText(captured);

      // Archive to History automatically
      const activeSpks = Array.from(
        new Set(
          speakerTurns.length > 0
            ? speakerTurns.map((s) => s.speaker)
            : [activeSpeaker]
        )
      );

      req("/api/meetings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: autoTitle,
          duration_seconds: recordingSeconds,
          transcript: captured,
          speakers: activeSpks,
          task_count: 0,
        }),
      })
        .then(() => req("/api/meetings"))
        .then((m) => setMeetings(m))
        .catch((e) => console.warn("Failed to archive meeting to history:", e));

      if (autoExtract) {
        setVoiceStudioOpen(false);
        notify("🎙️ Meeting saved to History! Analyzing tasks now...");
        executeIngest(autoTitle, captured);
      } else {
        setVoiceStudioOpen(false);
        setShowIngest(true);
        notify("🎙️ Meeting saved to History! Click 'Analyze source' to extract tasks.");
      }
    } else {
      if (!uploadText.trim()) {
        const fallbackText =
          "Action: Priya must send the revised launch plan by 2026-11-06. Alex has to update the deployment script by Friday.";
        setUploadTitle("Voice Memo (Sample)");
        setUploadText(fallbackText);
        setVoiceTranscript(fallbackText);
        setVoiceWordsCount(fallbackText.split(/\s+/).filter(Boolean).length);
        notify("No spoken audio captured. Loaded sample voice action item memo.");
      } else {
        notify("Voice recording ended.");
      }
    }
  }

  function loadDemoVoiceMemo(type: "launch" | "incident" | "strategy") {
    let text = "";
    if (type === "launch") {
      text = "Speaker 1 (Lead): Let's sync on Q4 release targets. Priya, what is your delivery timeline for the marketing deck?\nSpeaker 2 (Priya): I will deliver the revised launch plan and deck by 2026-11-06.\nSpeaker 3 (Alex): I will verify the database indexes and update the deployment script before Friday.";
      setSpeakerTurns([
        { id: "t1", speaker: "Speaker 1 (Lead)", text: "Let's sync on Q4 release targets. Priya, what is your delivery timeline for the marketing deck?", timestamp: "10:00:15 AM" },
        { id: "t2", speaker: "Speaker 2 (Priya)", text: "I will deliver the revised launch plan and deck by 2026-11-06.", timestamp: "10:00:32 AM" },
        { id: "t3", speaker: "Speaker 3 (Alex)", text: "I will verify the database indexes and update the deployment script before Friday.", timestamp: "10:00:48 AM" },
      ]);
    } else if (type === "incident") {
      text = "Speaker 1 (Lead): Emergency incident response: we detected credential leakage. Alex, revoke all API keys immediately.\nSpeaker 2 (Alex): Revoking keys now and rotating tokens. Security post-mortem meeting scheduled for 2026-11-04.";
      setSpeakerTurns([
        { id: "t1", speaker: "Speaker 1 (Lead)", text: "Emergency incident response: we detected credential leakage. Alex, revoke all API keys immediately.", timestamp: "11:15:02 AM" },
        { id: "t2", speaker: "Speaker 2 (Alex)", text: "Revoking keys now and rotating tokens. Security post-mortem meeting scheduled for 2026-11-04.", timestamp: "11:15:20 AM" },
      ]);
    } else {
      text = "Speaker 1 (Lead): Moving to executive strategy: Sarah, will vendor proposals be completed this month?\nSpeaker 2 (Sarah): Sarah to finalize Q4 vendor RFP proposals by 2026-11-15. Budget review approved with human signoff.";
      setSpeakerTurns([
        { id: "t1", speaker: "Speaker 1 (Lead)", text: "Moving to executive strategy: Sarah, will vendor proposals be completed this month?", timestamp: "02:30:10 PM" },
        { id: "t2", speaker: "Speaker 2 (Sarah)", text: "Sarah to finalize Q4 vendor RFP proposals by 2026-11-15. Budget review approved with human signoff.", timestamp: "02:30:35 PM" },
      ]);
    }
    transcriptRef.current = text;
    setVoiceTranscript(text);
    setVoiceWordsCount(text.split(/\s+/).filter(Boolean).length);
    setUploadText(text);
    notify("Loaded pitch scenario into Multi-Speaker Voice Studio!");
  }

  // Feature 2: 1-Click Demo Preset Loader
  async function handleLoadDemo(presetId: "product_launch" | "security_incident" | "exec_offsite") {
    setShowDemoMenu(false);
    setLoading(true);
    try {
      const res = await req("/api/demo/preset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset_id: presetId }),
      });
      await refresh();
      setActive("tasks");
      notify(`⚡ Demo loaded: ${res.title}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // Feature 3: Side-by-Side Source Context Inspector
  async function openSourceContext(docId: string, quote: string) {
    try {
      const doc = await req(`/api/documents/${docId}`);
      setSourceDocText({ title: doc.title, content: doc.content });
      setTargetHighlight(quote);
      setSourceInspectorOpen(true);
    } catch (e: any) {
      notify("Could not inspect source document: " + e.message);
    }
  }

  function renderHighlightedText(content: string, quote: string) {
    if (!quote || !content.includes(quote)) {
      return <span>{content}</span>;
    }
    const idx = content.indexOf(quote);
    const before = content.slice(0, idx);
    const after = content.slice(idx + quote.length);
    return (
      <span>
        {before}
        <mark className="evidence-highlight-mark">{quote}</mark>
        {after}
      </span>
    );
  }

  // Feature 4: AI Conflict Resolver
  async function resolveTaskConflict(task: Task, resolvedDate: string, rationale: string) {
    try {
      const updated = await req(`/api/tasks/${task.id}/resolve-conflict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolved_due_date: resolvedDate, rationale }),
      });
      await refresh();
      setSelected(updated);
      setConflictModalTask(null);
      notify(`Conflict resolved! Target deadline set to ${dateLabel(resolvedDate)}.`);
    } catch (e: any) {
      setError(e.message);
    }
  }

  // Feature 5: One-Click Action Dispatcher
  function openDispatchModal(t: Task) {
    setDispatchTask(t);
    setDispatchChannel("calendar");
    setDispatchTarget("");
    setDispatchSimulate(true);
    setDispatchFeedback(null);
    setDispatchModalOpen(true);
  }

  async function handleExecuteDispatch() {
    if (!dispatchTask) return;
    setDispatchLoading(true);
    try {
      const res = await req(`/api/tasks/${dispatchTask.id}/dispatch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel: dispatchChannel,
          target: dispatchTarget.trim() || undefined,
          simulate: dispatchSimulate,
        }),
      });
      await refresh();
      setDispatchFeedback(res.dispatch);
      notify(res.message || "Action successfully dispatched!");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDispatchLoading(false);
    }
  }

  // Auth Action Handlers
  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!authEmail.trim() || !authPassword.trim()) {
      setAuthError("Please enter your email and password.");
      return;
    }
    setAuthLoading(true);
    setAuthError("");
    setAuthNotice("");
    try {
      const res = await fetch(API + "/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw Error(data.detail || "Sign in failed");

      if (data.requires_verification) {
        setAuthMode("verify");
        setDevCode(data.dev_code || null);
        setAuthNotice(data.message || "Please verify your email address.");
      } else if (data.token) {
        localStorage.setItem("actionpilot_token", data.token);
        setToken(data.token);
        setCurrentUser(data.user);
        notify(`Welcome back, ${data.user.full_name || data.user.email}!`);
      }
    } catch (err: any) {
      setAuthError(formatApiError(err));
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    if (!authEmail.trim() || !authPassword.trim()) {
      setAuthError("Email and password are required.");
      return;
    }
    if (authPassword.length < 6) {
      setAuthError("Password must be at least 6 characters.");
      return;
    }
    setAuthLoading(true);
    setAuthError("");
    setAuthNotice("");
    try {
      const res = await fetch(API + "/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: authEmail,
          password: authPassword,
          full_name: authFullName,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw Error(data.detail || "Sign up failed");

      setAuthMode("verify");
      setDevCode(data.dev_code || null);
      setAuthNotice(data.message || "Verification code sent to your email.");
    } catch (err: any) {
      setAuthError(formatApiError(err));
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    if (!authCode.trim()) {
      setAuthError("Please enter the 6-digit verification code.");
      return;
    }
    setAuthLoading(true);
    setAuthError("");
    try {
      const res = await fetch(API + "/api/auth/verify-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, code: authCode.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw Error(data.detail || "Verification failed");

      localStorage.setItem("actionpilot_token", data.token);
      setToken(data.token);
      setCurrentUser(data.user);
      notify("Email verified successfully! Workspace ready.");
    } catch (err: any) {
      setAuthError(formatApiError(err));
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleResendCode() {
    setAuthLoading(true);
    setAuthError("");
    try {
      const res = await fetch(API + "/api/auth/resend-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail }),
      });
      const data = await res.json();
      if (!res.ok) throw Error(data.detail || "Could not resend code");

      setDevCode(data.dev_code || null);
      setAuthNotice(data.message || "A new code has been sent.");
      notify("New code sent!");
    } catch (err: any) {
      setAuthError(formatApiError(err));
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("actionpilot_token");
    setToken(null);
    setCurrentUser(null);
    setDocs([]);
    setTasks([]);
    setAudit([]);
    setAuthMode("login");
    setAuthPassword("");
    setAuthCode("");
    notify("You have signed out.");
  }

  // Workspace actions
  async function ingestText() {
    await executeIngest();
  }

  async function ingestFile(file?: File) {
    if (!file) return;
    setLoading(true);
    try {
      const f = new FormData();
      f.append("file", file);
      const r = await req("/api/documents", { method: "POST", body: f });
      await refresh();
      setShowIngest(false);
      setActive("tasks");
      notify(r.duplicate ? "Duplicate document skipped" : "Document processed and tasks extracted");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function taskAction(id: string, action: "approve" | "reject") {
    try {
      await req(`/api/tasks/${id}/${action}`, { method: "POST" });
      await refresh();
      setSelected((s) => (s?.id === id ? { ...s, status: action === "approve" ? "approved" : "rejected" } : s));
      notify(action === "approve" ? "Task approved" : "Task rejected");
    } catch (e: any) {
      setError(e.message);
    }
  }

  function openTask(t: Task) {
    setSelected(t);
    setEdit({
      title: t.title,
      assignee: t.assignee || "",
      due_date: t.due_date || "",
      priority: t.priority,
      description: t.description || "",
    });
  }

  async function saveTask() {
    if (!selected) return;
    try {
      const u = await req(`/api/tasks/${selected.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...edit, due_date: edit.due_date || null, assignee: edit.assignee || null }),
      });
      await refresh();
      setSelected(u);
      notify("Edits saved and audited");
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function createDraft() {
    if (!selected) return;
    try {
      await req(`/api/tasks/${selected.id}/draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...draft, recipient: draft.recipient || null }),
      });
      await refresh();
      setDraftOpen(false);
      notify("Draft saved — nothing was sent");
    } catch (e: any) {
      setError(e.message);
    }
  }

  const proposed = tasks.filter((t) => t.status === "proposed").length;
  const approved = tasks.filter((t) => t.status === "approved").length;
  const flagged = tasks.filter((t) => t.uncertainty_flags?.length > 0 && t.status !== "rejected").length;
  const visible = useMemo(
    () =>
      tasks.filter(
        (t) =>
          (statusFilter === "all" || t.status === statusFilter) &&
          `${t.title} ${t.assignee || ""} ${t.description}`.toLowerCase().includes(query.toLowerCase())
      ),
    [tasks, statusFilter, query]
  );
  const filteredAudit = audit.filter(
    (a) =>
      !auditFilter ||
      `${a.event_type} ${a.entity_id} ${JSON.stringify(a.details)}`.toLowerCase().includes(auditFilter.toLowerCase())
  );

  // Initial Authentication Checking Spinner
  if (authChecking) {
    return (
      <div className="auth-overlay">
        <div style={{ textAlign: "center", color: "#818cf8" }}>
          <LoaderCircle size={36} className="spin" style={{ margin: "auto" }} />
          <p style={{ marginTop: 14, fontSize: 13, color: "#94a3b8" }}>Connecting to ActionPilot...</p>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // Unauthenticated: Render Sign In / Sign Up / Verification
  // -------------------------------------------------------------
  if (!currentUser || !token) {
    return (
      <div className="auth-overlay">
        <button
          className="iconbtn"
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
          aria-label="Toggle theme"
          style={{ position: "fixed", top: 20, right: 24, zIndex: 100 }}
        >
          {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
        </button>
        <div className="auth-card">
          <div className="auth-brand">
            <div className="brandmark">
              <Workflow size={24} />
            </div>
            <h1>actionpilot</h1>
            <p>Evidence-Driven AI Workflow Automation</p>
          </div>

          {authError && (
            <div className="auth-error" style={{ marginBottom: 16 }}>
              <AlertTriangle size={16} />
              <span>{authError}</span>
            </div>
          )}

          {authNotice && (
            <div className="auth-notice" style={{ marginBottom: 16 }}>
              <Check size={16} />
              <span>{authNotice}</span>
            </div>
          )}

          {/* Verification View */}
          {authMode === "verify" ? (
            <form onSubmit={handleVerify} className="auth-form">
              <div style={{ textAlign: "center", marginBottom: 10 }}>
                <div
                  style={{
                    width: 48,
                    height: 48,
                    background: "#1e293b",
                    borderRadius: "50%",
                    display: "grid",
                    placeItems: "center",
                    margin: "0 auto 12px",
                    color: "#60a5fa",
                  }}
                >
                  <Mail size={22} />
                </div>
                <h3 style={{ margin: "0 0 6px", fontSize: 17, color: "#f8fafc" }}>Verify your email</h3>
                <p style={{ fontSize: 12, color: "#94a3b8", margin: 0 }}>
                  Enter the 6-digit code sent to <b>{authEmail}</b>
                </p>
              </div>

              {devCode && (
                <div className="auth-dev-badge">
                  <b>
                    <Sparkles size={14} /> Dev Mode OTP Code: <code style={{ color: "#60a5fa" }}>{devCode}</code>
                  </b>
                  <span>(SMTP is in local development mode)</span>
                  <button
                    type="button"
                    className="copy-code"
                    onClick={() => {
                      setAuthCode(devCode);
                      notify("Code filled!");
                    }}
                  >
                    Auto-fill code
                  </button>
                </div>
              )}

              <div className="otp-box">
                <input
                  className="otp-input"
                  maxLength={6}
                  placeholder="------"
                  value={authCode}
                  onChange={(e) => setAuthCode(e.target.value.replace(/\D/g, ""))}
                  autoFocus
                />
              </div>

              <button type="submit" className="auth-btn" disabled={authLoading || authCode.length < 4}>
                {authLoading ? <LoaderCircle size={16} className="spin" /> : <ShieldCheck size={16} />}
                Verify & Enter Workspace
              </button>

              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
                <button type="button" className="auth-link" onClick={handleResendCode} disabled={authLoading}>
                  Resend code
                </button>
                <button
                  type="button"
                  className="auth-link"
                  onClick={() => {
                    setAuthMode("login");
                    setAuthError("");
                    setAuthNotice("");
                  }}
                >
                  Back to Sign In
                </button>
              </div>
            </form>
          ) : (
            <>
              {/* Tab Selector: Sign In / Create Account */}
              <div className="auth-tabs">
                <button
                  type="button"
                  className={"auth-tab " + (authMode === "login" ? "active" : "")}
                  onClick={() => {
                    setAuthMode("login");
                    setAuthError("");
                    setAuthNotice("");
                  }}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  className={"auth-tab " + (authMode === "signup" ? "active" : "")}
                  onClick={() => {
                    setAuthMode("signup");
                    setAuthError("");
                    setAuthNotice("");
                  }}
                >
                  Create Account
                </button>
              </div>

              {authMode === "login" ? (
                /* Sign In Form */
                <form onSubmit={handleLogin} className="auth-form">
                  <div>
                    <label>Email Address</label>
                    <input
                      type="email"
                      required
                      className="auth-input"
                      placeholder="you@gmail.com"
                      value={authEmail}
                      onChange={(e) => setAuthEmail(e.target.value)}
                    />
                  </div>

                  <div>
                    <label>Password</label>
                    <input
                      type="password"
                      required
                      className="auth-input"
                      placeholder="••••••••"
                      value={authPassword}
                      onChange={(e) => setAuthPassword(e.target.value)}
                    />
                  </div>

                  <button type="submit" className="auth-btn" disabled={authLoading}>
                    {authLoading ? <LoaderCircle size={16} className="spin" /> : <Lock size={16} />}
                    Sign In to Workspace
                  </button>

                  <div style={{ textAlign: "center", marginTop: 8 }}>
                    <span style={{ fontSize: 11, color: "#94a3b8" }}>Don't have an account? </span>
                    <button
                      type="button"
                      className="auth-link"
                      onClick={() => {
                        setAuthMode("signup");
                        setAuthError("");
                      }}
                    >
                      Sign Up
                    </button>
                  </div>
                </form>
              ) : (
                /* Sign Up Form */
                <form onSubmit={handleSignup} className="auth-form">
                  <div>
                    <label>Full Name</label>
                    <input
                      type="text"
                      className="auth-input"
                      placeholder="e.g. Priya Sharma"
                      value={authFullName}
                      onChange={(e) => setAuthFullName(e.target.value)}
                    />
                  </div>

                  <div>
                    <label>Gmail / Email Address</label>
                    <input
                      type="email"
                      required
                      className="auth-input"
                      placeholder="you@gmail.com"
                      value={authEmail}
                      onChange={(e) => setAuthEmail(e.target.value)}
                    />
                  </div>

                  <div>
                    <label>Password (min. 6 characters)</label>
                    <input
                      type="password"
                      required
                      minLength={6}
                      className="auth-input"
                      placeholder="Create a strong password"
                      value={authPassword}
                      onChange={(e) => setAuthPassword(e.target.value)}
                    />
                  </div>

                  <button type="submit" className="auth-btn" disabled={authLoading}>
                    {authLoading ? <LoaderCircle size={16} className="spin" /> : <Mail size={16} />}
                    Create Account & Send Code
                  </button>

                  <div style={{ textAlign: "center", marginTop: 8 }}>
                    <span style={{ fontSize: 11, color: "#94a3b8" }}>Already have an account? </span>
                    <button
                      type="button"
                      className="auth-link"
                      onClick={() => {
                        setAuthMode("login");
                        setAuthError("");
                      }}
                    >
                      Sign In
                    </button>
                  </div>
                </form>
              )}
            </>
          )}
        </div>
        {toast && (
          <div className="toast">
            <Check size={15} />
            {toast}
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------
  // Authenticated: Render Main Application Workspace
  // -------------------------------------------------------------
  const userInitials =
    (currentUser.full_name || currentUser.email)
      .split(" ")
      .map((n) => n[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "U";

  return (
    <div className="shell">
      {/* Mobile Navigation Drawer Backdrop */}
      {mobileMenuOpen && (
        <div
          className="mobile-nav-backdrop"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside className={"sidebar " + (mobileMenuOpen ? "mobile-open" : "")}>
        <div className="brand">
          <div className="brandmark">
            <Workflow size={20} />
          </div>
          <div>
            <b>actionpilot</b>
            <small>WORKFLOW INTELLIGENCE</small>
          </div>
          <button
            className="mobile-close-btn"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <div className="workspace">
          <div className="workspace-icon">{userInitials[0]}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <b style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {currentUser.full_name || currentUser.email.split("@")[0]}'s Space
            </b>
            <small>Private Tenant</small>
          </div>
          <ChevronDown size={15} />
        </div>

        <div className="navlabel">WORKSPACE</div>
        {[
          ["overview", LayoutDashboard, "Overview"],
          ["tasks", ListTodo, "Task review"],
          ["documents", FileText, "Source documents"],
          ["history", Clock, "History"],
        ].map(([id, Icon, label]: any) => (
          <button
            key={id}
            className={"navitem " + (active === id ? "active" : "")}
            onClick={() => {
              setActive(id);
              setMobileMenuOpen(false);
            }}
          >
            <Icon size={17} />
            {label}
            {id === "tasks" && proposed > 0 && <span className="navcount">{proposed}</span>}
            {id === "history" && meetings.length > 0 && <span className="navcount">{meetings.length}</span>}
          </button>
        ))}

        <div className="navlabel" style={{ marginTop: 14 }}>PREFERENCES</div>
        {[
          ["settings", Settings, "Settings"],
          ["privacy", Shield, "Privacy & Policy"],
        ].map(([id, Icon, label]: any) => (
          <button
            key={id}
            className={"navitem " + (active === id ? "active" : "")}
            onClick={() => {
              setActive(id);
              setMobileMenuOpen(false);
            }}
          >
            <Icon size={17} />
            {label}
          </button>
        ))}

        {/* User Profile Card with Logout */}
        <div className="profile">
          <div className="avatar">{userInitials}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <b style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {currentUser.full_name || currentUser.email.split("@")[0]}
            </b>
            <small style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {currentUser.email}
            </small>
          </div>
          <button className="logout-btn" onClick={handleLogout} title="Sign Out">
            <LogOut size={14} />
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="mobile-menu-btn"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open navigation menu"
            >
              <Menu size={18} />
            </button>
            <div className="breadcrumb">
              Workspace <span>/</span>{" "}
              <b>
                {
                  (
                    {
                      overview: "Overview",
                      tasks: "Task review",
                      documents: "Source documents",
                      history: "Meeting History & Notes",
                      settings: "Settings & Personalization",
                      privacy: "Enterprise Privacy & Governance",
                    } as any
                  )[active]
                }
              </b>
            </div>
          </div>

          <div className="topright">
            {/* Live Voice Recording Mic Button in Topbar */}
            {isRecording ? (
              <button className="voice-record-btn recording" onClick={() => stopVoiceRecording(true)}>
                <div className="voice-bars">
                  <div className="voice-bar" />
                  <div className="voice-bar" />
                  <div className="voice-bar" />
                  <div className="voice-bar" />
                  <div className="voice-bar" />
                </div>
                <span>Rec {recordingSeconds}s</span>
                <b>Stop & Extract</b>
              </button>
            ) : (
              <button className="voice-record-btn" onClick={startVoiceRecording} title="Record Meeting Voice Note">
                <Mic size={14} /> Record Note
              </button>
            )}

            <span className="user-badge-top" title={currentUser.email}>
              <ShieldCheck size={14} /> <span className="email-text">{currentUser.email}</span>
            </span>
            <button
              className="iconbtn"
              onClick={toggleTheme}
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
              aria-label="Toggle color theme"
            >
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </button>
          </div>
        </header>

        <div className="content">
          {error && (
            <div className="error">
              <AlertTriangle size={17} />
              {error}
              {health === "offline" ? " — start the FastAPI server using README instructions." : ""}
              <button onClick={() => setError("")}>
                <X size={15} />
              </button>
            </div>
          )}

          {active === "overview" && (
            <>
              <div className="heading">
                <div>
                  <div className="eyebrow">
                    <Sparkles size={13} /> EVIDENCE-DRIVEN WORKFLOW INTELLIGENCE
                  </div>
                  <h1>{getGreeting()}, {currentUser.full_name || currentUser.email.split("@")[0]}.</h1>
                  <p>Transform unstructured voice notes, emails & documents into verified, human-governed work.</p>
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                  <button className="secondary" onClick={startVoiceRecording}>
                    <Mic size={15} /> Voice memo
                  </button>
                  <button className="primary" onClick={() => setShowIngest(true)}>
                    <Plus size={16} /> New workflow
                  </button>
                </div>
              </div>

              <div className="trustbanner">
                <div className="trusticon">
                  <ShieldCheck size={22} />
                </div>
                <div>
                  <b>Evidence-Backed Automation & Human Governance</b>
                  <p>
                    Every proposal is anchored to source document citations with confidence scoring. Actions remain gated until explicitly approved by a human operator.
                  </p>
                </div>
                <span>● APPROVAL GATE ACTIVE</span>
              </div>

              <div className="sectionhead">
                <div>
                  <h2>Workflow overview</h2>
                  <p>Live summary of your workspace activity</p>
                </div>
                <small>◉ Auto-refreshes every 12 sec</small>
              </div>

              <div className="stats">
                {[
                  [FileText, "Source documents", docs.length, "Ingested & indexed", "blue"],
                  [ListTodo, "Proposed tasks", proposed, "Awaiting human review", "purple"],
                  [AlertTriangle, "Items flagged", flagged, "Discrepancies & missing fields", "amber"],
                  [CheckCheck, "Approved tasks", approved, "Ready for external dispatch", "green"],
                ].map(([I, l, v, h, t]: any) => (
                  <div className="stat" key={l}>
                    <div className={"staticon " + t}>
                      <I size={18} />
                    </div>
                    <span>{l}</span>
                    <strong>{v}</strong>
                    <small>{h}</small>
                  </div>
                ))}
              </div>

              <div className="twocol">
                <section className="panel">
                  <div className="panelhead">
                    <div>
                      <h3>Processing pipeline</h3>
                      <p>From unstructured source material to verified external action</p>
                    </div>
                    <Badge tone="blue">PIPELINE ACTIVE</Badge>
                  </div>
                  {[
                    [
                      "01",
                      FileText,
                      "Ingest source",
                      "Text notes, audio memos, and PDF documents",
                      docs.length ? "Completed" : "Ready",
                      docs.length ? "done" : "",
                    ],
                    [
                      "02",
                      Sparkles,
                      "Extract & validate",
                      "Schema-checked task proposals & uncertainty detection",
                      docs.length ? "Completed" : "Waiting",
                      docs.length ? "done" : "",
                    ],
                    [
                      "03",
                      AlertTriangle,
                      "Review & resolve",
                      "Side-by-side evidence inspection & discrepancy diffing",
                      flagged ? `${flagged} flagged` : proposed ? `${proposed} pending` : "Ready",
                      flagged ? "warn" : proposed ? "info" : "",
                    ],
                    [
                      "04",
                      ShieldCheck,
                      "Human approval & dispatch",
                      "1-click Google Calendar, Slack, GitHub, or Email dispatch",
                      approved ? `${approved} ready` : "Standing by",
                      approved ? "done" : "",
                    ],
                  ].map(([n, I, t, s, state, tone]: any, i) => (
                    <div className="pipe" key={n}>
                      <div className={"pipeicon p" + i}>
                        <I size={17} />
                      </div>
                      <div className="pipecopy">
                        <b>{t}</b>
                        <small>{s}</small>
                      </div>
                      <span className={"pipe-status " + tone}>{state}</span>
                      <em>{n}</em>
                    </div>
                  ))}
                  <button className="textbtn" onClick={() => setActive("tasks")}>
                    Review proposed tasks <ArrowUpRight size={15} />
                  </button>
                </section>

                <section className="panel">
                  <div className="panelhead">
                    <div>
                      <h3>Recent task proposals</h3>
                      <p>Action items requiring validation or dispatch</p>
                    </div>
                    <button className="subtle" onClick={() => setActive("tasks")}>
                      View all ↗
                    </button>
                  </div>
                  {tasks.slice(0, 5).map((t) => (
                    <button className="recent" key={t.id} onClick={() => openTask(t)}>
                      <span className="recenticon">
                        <FileText size={16} />
                      </span>
                      <span className="recentcopy">
                        <b>{t.title}</b>
                        <small>
                          {t.assignee || "Owner unassigned"} · {dateLabel(t.due_date)}
                          {t.dispatched ? ` · Dispatched via ${t.dispatch_channel}` : ""}
                        </small>
                      </span>
                      <Badge tone={t.status === "approved" ? "green" : t.status === "rejected" ? "red" : "amber"}>
                        {t.status}
                      </Badge>
                    </button>
                  ))}
                  {!tasks.length && (
                    <Empty
                      title="No task proposals yet"
                      text="Ingest meeting notes, voice memos, or documents to test evidence-backed task extraction."
                      action={() => setShowIngest(true)}
                      btnText="Ingest Document"
                      icon={ListTodo}
                    />
                  )}
                </section>
              </div>
            </>
          )}

          {active === "tasks" && (
            <>
              <div className="heading">
                <div>
                  <div className="eyebrow">
                    <ListTodo size={14} /> REVIEW & APPROVAL
                  </div>
                  <h1>Task review</h1>
                  <p>Validate evidence, resolve conflicts with AI, and dispatch approved actions.</p>
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                  <button className="primary" onClick={() => setShowIngest(true)}>
                    <Plus size={17} /> New workflow
                  </button>
                </div>
              </div>

              <div className="strip">
                <div>
                  <b>{tasks.length}</b>
                  <span>Total proposals</span>
                </div>
                <div>
                  <b>{proposed}</b>
                  <span>Awaiting review</span>
                </div>
                <div>
                  <b>{tasks.filter((t) => t.uncertainty_flags.some((f) => f.toLowerCase().includes("conflict"))).length}</b>
                  <span>Conflict-flagged</span>
                </div>
                <div>
                  <b>{approved}</b>
                  <span>Approved for dispatch</span>
                </div>
              </div>

              <div className="toolbar">
                <div className="search">
                  <Search size={16} />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search tasks, owners, evidence..."
                  />
                </div>
                <div className="filter">
                  <Filter size={15} />
                  <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                    <option value="all">All statuses</option>
                    <option value="proposed">Proposed</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>
              </div>

              {visible.map((t) => (
                <TaskCard
                  key={t.id}
                  t={t}
                  open={() => openTask(t)}
                  approve={() => taskAction(t.id, "approve")}
                  reject={() => taskAction(t.id, "reject")}
                  onResolveConflict={() => setConflictModalTask(t)}
                  onOpenSource={(q) => openSourceContext(t.document_id, q)}
                  onDispatch={() => openDispatchModal(t)}
                />
              ))}
              {!visible.length && (
                <Empty
                  title="No matching tasks"
                  text="Extract tasks from notes, emails, or documents to review them here."
                  action={() => setShowIngest(true)}
                  btnText="New workflow"
                />
              )}
            </>
          )}

          {active === "documents" && (
            <>
              <div className="heading">
                <div>
                  <div className="eyebrow">
                    <FileText size={14} /> SOURCE LIBRARY
                  </div>
                  <h1>Source documents</h1>
                  <p>Original source material stays available for traceability.</p>
                </div>
                <button className="primary" onClick={() => setShowIngest(true)}>
                  <Plus size={17} /> Add document
                </button>
              </div>
              <section className="panel">
                <div className="panelhead">
                  <div>
                    <h3>Ingested sources</h3>
                    <p>{docs.length} documents in your workspace</p>
                  </div>
                  <Badge>{docs.length} SOURCES</Badge>
                </div>
                {docs.map((d) => (
                  <div className="docrow" key={d.id}>
                    <FileText />
                    <div>
                      <b>{d.title}</b>
                      <small>
                        {d.filename || "Pasted text"} · {timeLabel(d.created_at)}
                      </small>
                    </div>
                    <button
                      className="evidence-inspector-btn"
                      onClick={() => openSourceContext(d.id, "")}
                      style={{ marginRight: 12 }}
                    >
                      <FileText size={13} /> View Text
                    </button>
                    <span>{d.task_count} tasks</span>
                    <Badge tone="green">{d.status}</Badge>
                  </div>
                ))}
                {!docs.length && (
                  <Empty
                    title="Your source library is empty"
                    text="Upload a PDF or paste meeting notes to begin."
                    action={() => setShowIngest(true)}
                  />
                )}
              </section>
            </>
          )}

          {active === "audit" && (
            <>
              <div className="heading">
                <div>
                  <div className="eyebrow">
                    <History size={14} /> ACCOUNTABILITY
                  </div>
                  <h1>Audit trail</h1>
                  <p>Chronological record of ingestion, edits, conflict resolutions, approvals, and live dispatches.</p>
                </div>
                <Badge tone="green">APPEND-ONLY EVENTS</Badge>
              </div>
              <div className="toolbar">
                <div className="search">
                  <Search size={16} />
                  <input
                    value={auditFilter}
                    onChange={(e) => setAuditFilter(e.target.value)}
                    placeholder="Search event type, ID, or details..."
                  />
                </div>
                <span>{filteredAudit.length} events</span>
              </div>
              <section className="panel">
                {filteredAudit.map((a) => (
                  <AuditRow key={a.id} a={a} detailed />
                ))}
                {!filteredAudit.length && (
                  <Empty title="No audit events found" text="Activity will appear here as you use ActionPilot." />
                )}
              </section>
            </>
          )}

          {active === "history" && (
            <>
              <div className="heading">
                <div>
                  <div className="eyebrow">
                    <Clock size={14} /> VOICE MEMO & MEETING ARCHIVE
                  </div>
                  <h1>Meeting notes & history</h1>
                  <p>All recorded voice memos and multi-voice conferences are saved here with diarized transcripts and task extraction.</p>
                </div>
                <button className="primary" onClick={startVoiceRecording}>
                  <Mic size={14} /> New Voice Recording
                </button>
              </div>

              <div className="toolbar">
                <div className="search">
                  <Search size={16} />
                  <input
                    value={meetingSearch}
                    onChange={(e) => setMeetingSearch(e.target.value)}
                    placeholder="Search meetings by title, transcript text, or attendee..."
                  />
                </div>
                <span>
                  {meetings.filter((m) =>
                    (m.title + " " + m.transcript + " " + (m.speakers || []).join(" "))
                      .toLowerCase()
                      .includes(meetingSearch.toLowerCase())
                  ).length}{" "}
                  recordings
                </span>
              </div>

              {meetings.length === 0 ? (
                <Empty
                  title="No meeting recordings yet"
                  text="Record live meetings with the mic button above, or click below to start your first session."
                  action={startVoiceRecording}
                />
              ) : (
                <div className="history-grid">
                  {meetings
                    .filter((m) =>
                      (m.title + " " + m.transcript + " " + (m.speakers || []).join(" "))
                        .toLowerCase()
                        .includes(meetingSearch.toLowerCase())
                    )
                    .map((m) => (
                      <div className="meeting-card" key={m.id}>
                        <div className="meeting-card-header">
                          <div>
                            <h3>{m.title}</h3>
                            <small>
                              <Clock size={11} style={{ display: "inline", verticalAlign: "middle", marginRight: 3 }} />
                              {timeLabel(m.recorded_at)} • {Math.floor(m.duration_seconds / 60)}m{" "}
                              {m.duration_seconds % 60}s
                            </small>
                          </div>
                        </div>

                        <div className="meeting-tags-row">
                          {(m.speakers && m.speakers.length > 0 ? m.speakers : ["Lead"]).map((spk, i) => (
                            <span className="meeting-tag highlight" key={i}>
                              <Users size={11} /> {spk}
                            </span>
                          ))}
                          <span className="meeting-tag">
                            <ListTodo size={11} /> {m.task_count} tasks
                          </span>
                        </div>

                        <div className="meeting-transcript-preview" title="Transcript snippet">
                          {m.transcript}
                        </div>

                        <div className="meeting-actions-row">
                          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                            <button
                              className="btn"
                              style={{ fontSize: 11, padding: "5px 9px" }}
                              onClick={() => setActiveMeetingModal(m)}
                            >
                              <FileText size={12} /> View Notes
                            </button>
                            <button
                              className="btn"
                              style={{ fontSize: 11, padding: "5px 9px" }}
                              onClick={() => {
                                setUploadTitle(m.title);
                                setUploadText(m.transcript);
                                setShowIngest(true);
                              }}
                            >
                              <Sparkles size={12} /> Extract Tasks
                            </button>
                          </div>
                          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                            <button
                              className="iconbtn"
                              title="Copy full transcript"
                              onClick={() => {
                                navigator.clipboard.writeText(m.transcript);
                                notify("Meeting transcript copied to clipboard!");
                              }}
                            >
                              <Copy size={13} />
                            </button>
                            <button
                              className="iconbtn"
                              title="Delete meeting"
                              onClick={() => handleDeleteMeeting(m.id)}
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </>
          )}

          {active === "settings" && (
            <>
              <div className="heading">
                <div>
                  <div className="eyebrow">
                    <Settings size={14} /> USER PREFERENCES & ACCOUNT
                  </div>
                  <h1>Settings & Personalization</h1>
                  <p>Update your personal details, email, contact information, and customize AI audio engine behavior.</p>
                </div>
                <Badge tone="blue">TENANT: {currentUser.id.substring(0, 8)}</Badge>
              </div>

              <div className="settings-layout">
                {profileNotice && (
                  <div className="auth-notice" style={{ margin: 0 }}>
                    {profileNotice}
                  </div>
                )}
                {profileError && (
                  <div className="auth-error" style={{ margin: 0 }}>
                    {profileError}
                  </div>
                )}

                {/* Section 1: Personal & Contact Information */}
                <form className="settings-section-card" onSubmit={handleSaveProfile}>
                  <h3>
                    <Users size={16} /> Personal Information & Credentials
                  </h3>
                  <p>Update your display name, login email, phone number, and age for your workspace account.</p>

                  <div className="settings-form-grid">
                    <div className="settings-field">
                      <label>Full Name</label>
                      <input
                        type="text"
                        value={profileName}
                        onChange={(e) => setProfileName(e.target.value)}
                        placeholder="e.g. Alex Morgan"
                        required
                      />
                    </div>

                    <div className="settings-field">
                      <label>Email Address</label>
                      <input
                        type="email"
                        value={profileEmail}
                        onChange={(e) => setProfileEmail(e.target.value)}
                        placeholder="e.g. alex@company.com"
                        required
                      />
                    </div>

                    <div className="settings-field">
                      <label>Contact Number (Phone)</label>
                      <input
                        type="tel"
                        value={profilePhone}
                        onChange={(e) => setProfilePhone(e.target.value)}
                        placeholder="+1 (555) 234-5678"
                      />
                    </div>

                    <div className="settings-field">
                      <label>Age</label>
                      <input
                        type="number"
                        min="16"
                        max="120"
                        value={profileAge}
                        onChange={(e) => setProfileAge(e.target.value ? Number(e.target.value) : "")}
                        placeholder="e.g. 29"
                      />
                    </div>

                    <div className="settings-field" style={{ gridColumn: "1 / -1" }}>
                      <label>Job Title / Role</label>
                      <input
                        type="text"
                        value={profileJobTitle}
                        onChange={(e) => setProfileJobTitle(e.target.value)}
                        placeholder="e.g. Principal Product Manager & Release Lead"
                      />
                    </div>
                  </div>

                  <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
                    <button type="submit" className="primary" disabled={profileSaving}>
                      {profileSaving ? "Saving changes..." : "Save Profile Information"}
                    </button>
                  </div>
                </form>

                {/* Section 2: Workspace Customization */}
                <div className="settings-section-card">
                  <h3>
                    <Sparkles size={16} /> Application & Voice Customization
                  </h3>
                  <p>Fine-tune audio capture sensitivity, conference diarization, and visual workspace preferences.</p>

                  <div>
                    <div className="settings-toggle-row">
                      <div>
                        <b>Color Theme</b>
                        <small>Switch between dark obsidian theme and high-contrast light theme.</small>
                      </div>
                      <button className="btn" type="button" onClick={toggleTheme}>
                        {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />} {theme === "dark" ? "Switch to Light" : "Switch to Dark"}
                      </button>
                    </div>

                    <div className="settings-toggle-row">
                      <div>
                        <b>Multi-Voice Conference Capture (Max Room Voices)</b>
                        <small>Disables aggressive browser acoustic echo suppression to capture all voices in the room.</small>
                      </div>
                      <input
                        type="checkbox"
                        checked={multiSpeakerMode}
                        onChange={(e) => setMultiSpeakerMode(e.target.checked)}
                        style={{ width: 18, height: 18, cursor: "pointer" }}
                      />
                    </div>

                    <div className="settings-toggle-row">
                      <div>
                        <b>High-Fidelity Stereo Audio Stream</b>
                        <small>Requests 2-channel 48kHz audio streams for improved acoustic voice distinction.</small>
                      </div>
                      <input
                        type="checkbox"
                        checked={appCustomization.highFidelityMode}
                        onChange={(e) =>
                          setAppCustomization((p) => ({ ...p, highFidelityMode: e.target.checked }))
                        }
                        style={{ width: 18, height: 18, cursor: "pointer" }}
                      />
                    </div>

                    <div className="settings-toggle-row">
                      <div>
                        <b>Intelligent Auto-Punctuation</b>
                        <small>Automatically structures stream transcription with sentence boundaries and action tokens.</small>
                      </div>
                      <input
                        type="checkbox"
                        checked={appCustomization.autoPunctuate}
                        onChange={(e) =>
                          setAppCustomization((p) => ({ ...p, autoPunctuate: e.target.checked }))
                        }
                        style={{ width: 18, height: 18, cursor: "pointer" }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {active === "privacy" && (
            <>
              <div className="heading">
                <div>
                  <div className="eyebrow">
                    <ShieldCheck size={14} /> TRUST & GOVERNANCE
                  </div>
                  <h1>Privacy & Security Policy</h1>
                  <p>Enterprise-grade security, zero AI model training on customer data, and strict cryptographic multi-tenancy.</p>
                </div>
                <Badge tone="green">SOC-2 READY ARCHITECTURE</Badge>
              </div>

              <div className="privacy-container">
                <div className="privacy-hero-card">
                  <h2>Zero AI Model Training Guarantee</h2>
                  <p>
                    ActionPilot strictly processes your voice memos, audio transcripts, and task extractions in memory and within your dedicated private database tenant. Your proprietary business data, meeting discussions, and internal action items are <b>never used to train, fine-tune, or improve foundational AI models</b>.
                  </p>
                </div>

                <div className="privacy-grid">
                  <div className="privacy-clause-card">
                    <h4>
                      <Shield size={16} color="var(--primary)" /> Cryptographic Multi-Tenancy
                    </h4>
                    <p>
                      Every user account is bound to a distinct workspace tenant ID. SQL queries, document uploads, and tasks are strictly scoped at the database level with parameterized queries.
                    </p>
                  </div>

                  <div className="privacy-clause-card">
                    <h4>
                      <Users size={16} color="var(--primary)" /> Multi-Speaker Audio Governance
                    </h4>
                    <p>
                      Voice recordings and conference diarizations remain strictly within your session. Audio streams are captured via secure in-browser Web Audio APIs and transmitted only over TLS 1.3 encrypted sockets.
                    </p>
                  </div>

                  <div className="privacy-clause-card">
                    <h4>
                      <Sparkles size={16} color="var(--primary)" /> Human-in-the-Loop Safeguards
                    </h4>
                    <p>
                      ActionPilot adheres to strict AI safety principles: all extracted tasks remain in a "Proposed" state until an authorized human reviews, modifies, or confirms them. No automated external dispatches occur without human authorization.
                    </p>
                  </div>

                  <div className="privacy-clause-card">
                    <h4>
                      <FileText size={16} color="var(--primary)" /> Immutable Audit Accountability
                    </h4>
                    <p>
                      Every state mutation, AI task extraction, conflict resolution, and channel dispatch is logged in an append-only audit ledger with cryptographic timestamps and actor attribution.
                    </p>
                  </div>

                  <div className="privacy-clause-card">
                    <h4>
                      <Lock size={16} color="var(--primary)" /> Data Encryption at Rest & In-Transit
                    </h4>
                    <p>
                      Workspace documents and database credentials use industry-standard AES-256 encryption at rest on Neon PostgreSQL clusters and TLS 1.3 in transit with strict channel binding.
                    </p>
                  </div>

                  <div className="privacy-clause-card">
                    <h4>
                      <Trash2 size={16} color="var(--primary)" /> Data Portability & Complete Deletion
                    </h4>
                    <p>
                      You maintain 100% intellectual property ownership of your transcripts, notes, and task graphs. You can export or permanently delete your meetings and source documents at any time.
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>

      {/* Voice Intelligence Studio Modal */}
      {voiceStudioOpen && (
        <div
          className="voice-studio-overlay"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) stopVoiceRecording(false);
          }}
        >
          <div className="voice-studio-card">
            <div className="voice-studio-header">
              <div className="voice-studio-brand">
                <div className={"voice-mic-orb" + (isRecording ? " active" : "")}>
                  <Mic size={18} />
                </div>
                <div>
                  <b style={{ fontSize: 14, color: "var(--text-primary)", display: "block" }}>
                    Voice Intelligence Studio
                  </b>
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                    Real-time speech-to-intent analysis & evidence extraction
                  </span>
                </div>
              </div>
              <button
                className="iconbtn"
                onClick={() => stopVoiceRecording(false)}
                title="Close Studio"
              >
                <X size={16} />
              </button>
            </div>

            <div className="voice-studio-body">
              {/* Telemetry Bar */}
              <div className="voice-telemetry-row">
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      fontWeight: 700,
                      color: isRecording ? "var(--danger)" : "var(--text-muted)",
                      fontSize: 11,
                      letterSpacing: "0.04em",
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: isRecording ? "var(--danger)" : "var(--text-muted)",
                        boxShadow: isRecording ? "0 0 8px rgba(239, 68, 68, 0.7)" : "none",
                      }}
                    />
                    {isRecording ? "LISTENING (CONTINUOUS)" : "RECORDING PAUSED"}
                  </span>
                  <span style={{ color: "var(--border-card)" }}>|</span>
                  <span style={{ color: "var(--text-secondary)", fontWeight: 600 }}>
                    <Clock3 size={12} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
                    {Math.floor(recordingSeconds / 60)}:{(recordingSeconds % 60).toString().padStart(2, "0")}s
                  </span>
                  <span style={{ color: "var(--border-card)" }}>|</span>
                  <span style={{ color: "var(--text-secondary)" }}>
                    <b>{voiceWordsCount}</b> words spoken
                  </span>
                </div>

                <div className="voice-meter-wrap" title="Microphone Input Level">
                  <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Mic Level</span>
                  <div className="voice-meter-track">
                    <div
                      className="voice-meter-fill"
                      style={{ width: `${Math.max(8, isRecording ? audioLevel : 0)}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Multi-Speaker Conference Diarization Bar */}
              <div style={{ margin: "14px 0 8px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 5 }}>
                    <Volume2 size={13} color="var(--primary)" /> MULTI-VOICE CONFERENCE (MAX ROOM VOICES)
                  </span>
                  <span style={{ fontSize: 10, color: "var(--text-muted)" }}>Omnidirectional High Sensitivity Active</span>
                </div>

                <div className="speaker-selector-bar">
                  <span style={{ fontSize: 11, color: "var(--text-muted)", marginRight: 4 }}>Active Voice:</span>
                  {availableSpeakers.map((spk) => (
                    <button
                      key={spk}
                      type="button"
                      className={"speaker-pill-btn " + (activeSpeaker === spk ? "active" : "")}
                      onClick={() => handleSelectSpeaker(spk)}
                    >
                      <span className="speaker-dot" />
                      {spk}
                    </button>
                  ))}
                  <button
                    type="button"
                    className="speaker-pill-btn"
                    onClick={handleAddSpeaker}
                    title="Add another speaker in room"
                  >
                    <Plus size={11} /> Add Speaker
                  </button>
                </div>
              </div>

              {/* Live Canvas */}
              <div className="voice-transcript-canvas">
                {speakerTurns.length > 0 ? (
                  <div className="multi-speaker-turns-list">
                    {speakerTurns.map((turn, idx) => (
                      <div className="speaker-turn-card" key={turn.id || idx}>
                        <div className={"speaker-turn-avatar spk-" + (idx % 4)}>
                          {turn.speaker.charAt(0) || "S"}
                        </div>
                        <div className="speaker-turn-content">
                          <b>
                            {turn.speaker} <span style={{ opacity: 0.6, fontWeight: 400 }}>• {turn.timestamp}</span>
                          </b>
                          <p>{turn.text}</p>
                        </div>
                      </div>
                    ))}
                    {voiceTranscript && isRecording && (
                      <div className="speaker-turn-card" style={{ opacity: 0.85, borderStyle: "dashed" }}>
                        <div className="speaker-turn-avatar spk-0">{activeSpeaker.charAt(0)}</div>
                        <div className="speaker-turn-content">
                          <b>{activeSpeaker} (speaking...)</b>
                          <p>
                            {voiceTranscript}
                            <span className="voice-pulse-cursor" />
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ) : voiceTranscript ? (
                  <div>
                    <div style={{ marginBottom: 6, fontSize: 11, fontWeight: 600, color: "var(--primary)" }}>
                      Current Speaker: {activeSpeaker}
                    </div>
                    <span>{voiceTranscript}</span>
                    {isRecording && <span className="voice-pulse-cursor" />}
                  </div>
                ) : (
                  <div className="voice-empty-prompt">
                    <p>
                      🎙️ <b>Start speaking naturally into your microphone...</b>
                      <br />
                      Mention action items, deadlines, assignees, or project requirements.
                    </p>
                    <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                      Quick pitch samples (click to test immediately):
                      <div className="voice-sample-chips">
                        <button
                          type="button"
                          className="voice-chip"
                          onClick={() => loadDemoVoiceMemo("launch")}
                        >
                          🚀 Launch Sync (Priya deadline & review)
                        </button>
                        <button
                          type="button"
                          className="voice-chip"
                          onClick={() => loadDemoVoiceMemo("incident")}
                        >
                          🚨 Security Incident (Alex API revoke)
                        </button>
                        <button
                          type="button"
                          className="voice-chip"
                          onClick={() => loadDemoVoiceMemo("strategy")}
                        >
                          📊 Strategy Offsite (Sarah RFP milestones)
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Detected Action Indicator */}
              {voiceTranscript && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "8px 12px",
                    background: "var(--primary-subtle)",
                    border: "1px solid var(--primary-border)",
                    borderRadius: "var(--radius-md)",
                    fontSize: 12,
                    color: "var(--primary)",
                  }}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 600 }}>
                    <Sparkles size={14} /> AI Ready: Evidence-linked extraction will parse actions & assignees
                  </span>
                  <span style={{ fontSize: 11, opacity: 0.85 }}>Human approval gate active</span>
                </div>
              )}
            </div>

            <div className="voice-studio-foot">
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                {isRecording ? (
                  <button
                    className="btn"
                    onClick={() => {
                      isExplicitlyRecordingRef.current = false;
                      setIsRecording(false);
                      if (recognitionRef.current) try { recognitionRef.current.stop(); } catch {}
                    }}
                  >
                    <MicOff size={14} /> Pause
                  </button>
                ) : (
                  <button className="btn" onClick={startVoiceRecording}>
                    <Mic size={14} /> Resume
                  </button>
                )}
                <button
                  className="btn"
                  onClick={() => {
                    accumulatedTranscriptRef.current = "";
                    transcriptRef.current = "";
                    setVoiceTranscript("");
                    setSpeakerTurns([]);
                    setVoiceWordsCount(0);
                    setRecordingSeconds(0);
                    notify("Transcript and speaker turns reset.");
                  }}
                >
                  <RefreshCw size={13} /> Clear
                </button>
              </div>

              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <button
                  className="btn"
                  onClick={() => stopVoiceRecording(false)}
                  disabled={!voiceTranscript.trim()}
                  title="Open this note in the standard editor"
                >
                  📝 Open in Editor
                </button>
                <button
                  className="primary"
                  onClick={() => stopVoiceRecording(true)}
                  disabled={!voiceTranscript.trim() || loading}
                  style={{ minWidth: 170 }}
                >
                  {loading ? (
                    <LoaderCircle className="spin" size={15} />
                  ) : (
                    <>
                      <Sparkles size={15} /> Stop & Extract Tasks
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Meeting Notes Inspector Modal */}
      {activeMeetingModal && (
        <div
          className="modal-overlay"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setActiveMeetingModal(null);
          }}
        >
          <div className="modal" style={{ maxWidth: 680 }}>
            <div className="modal-header">
              <div>
                <h3 style={{ margin: 0, fontSize: 16 }}>{activeMeetingModal.title}</h3>
                <small style={{ color: "var(--text-muted)", fontSize: 11 }}>
                  Recorded {timeLabel(activeMeetingModal.recorded_at)} • Duration:{" "}
                  {Math.floor(activeMeetingModal.duration_seconds / 60)}m{" "}
                  {activeMeetingModal.duration_seconds % 60}s
                </small>
              </div>
              <button className="iconbtn" onClick={() => setActiveMeetingModal(null)}>
                <X size={16} />
              </button>
            </div>

            <div style={{ padding: "16px 20px" }}>
              <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
                {(activeMeetingModal.speakers && activeMeetingModal.speakers.length > 0
                  ? activeMeetingModal.speakers
                  : ["Lead"]
                ).map((s, i) => (
                  <span className="meeting-tag highlight" key={i}>
                    <Users size={11} /> {s}
                  </span>
                ))}
              </div>

              <div
                style={{
                  background: "var(--bg-subtle)",
                  border: "1px solid var(--border-card)",
                  borderRadius: "var(--radius-md)",
                  padding: 14,
                  fontSize: 12.5,
                  lineHeight: 1.7,
                  color: "var(--text-primary)",
                  maxHeight: 340,
                  overflowY: "auto",
                  whiteSpace: "pre-wrap",
                }}
              >
                {activeMeetingModal.transcript}
              </div>
            </div>

            <div className="modal-actions" style={{ justifyContent: "space-between" }}>
              <button
                className="btn"
                onClick={() => {
                  navigator.clipboard.writeText(activeMeetingModal.transcript);
                  notify("Meeting transcript copied to clipboard!");
                }}
              >
                <Copy size={13} /> Copy Transcript
              </button>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  className="btn"
                  onClick={() => setActiveMeetingModal(null)}
                >
                  Close
                </button>
                <button
                  className="primary"
                  onClick={() => {
                    const m = activeMeetingModal;
                    setActiveMeetingModal(null);
                    setUploadTitle(m.title);
                    setUploadText(m.transcript);
                    setShowIngest(true);
                  }}
                >
                  <Sparkles size={13} /> Extract Tasks with AI
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Ingest text or file */}
      {showIngest && (
        <div
          className="backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setShowIngest(false);
          }}
        >
          <section className="modal">
            <div className="modalhead">
              <div>
                <div className="eyebrow">
                  <Sparkles size={13} /> START A WORKFLOW
                </div>
                <h2>Bring your source material</h2>
                <p>Extract candidate actions with evidence attached.</p>
              </div>
              <button className="iconbtn" onClick={() => setShowIngest(false)}>
                <X />
              </button>
            </div>

            {/* Mic / Voice Recording Quick Trigger inside Modal */}
            <div
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-card)",
                borderRadius: 10,
                padding: 14,
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <b style={{ color: "var(--text-primary)", fontSize: 13, fontWeight: 600 }}>🎙️ Voice Meeting Note</b>
                <p style={{ color: "var(--text-secondary)", fontSize: 12, margin: "2px 0 0" }}>
                  Record a voice memo directly — speech streams into the notes box in real time
                </p>
              </div>
              {isRecording ? (
                <button className="voice-record-btn recording" onClick={() => stopVoiceRecording(false)}>
                  <MicOff size={14} /> Stop ({recordingSeconds}s)
                </button>
              ) : (
                <button className="voice-record-btn" onClick={startVoiceRecording}>
                  <Mic size={14} /> Start Voice Recording
                </button>
              )}
            </div>

            {voiceTranscript && (
              <div className="voice-transcript-card" style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontSize: 11, color: "var(--info)", fontWeight: 700, display: "flex", alignItems: "center", gap: 6, letterSpacing: "0.04em" }}>
                    ● {isRecording ? "LIVE TRANSCRIPTION (STREAMING TO NOTES)..." : "TRANSCRIPTION CAPTURED"}
                  </span>
                  {!isRecording && (
                    <span style={{ fontSize: 11, color: "var(--success)", fontWeight: 600 }}>
                      ✓ Added to notes box below
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 13, lineHeight: 1.5, color: "var(--text-primary)" }}>
                  {voiceTranscript}
                </div>
                {!isRecording && (
                  <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      className="btn"
                      style={{ fontSize: 12, padding: "5px 12px", height: "auto" }}
                      onClick={() => {
                        setUploadText(voiceTranscript);
                        notify("Spoken text copied into notes box below.");
                      }}
                    >
                      🔄 Re-insert to notes box
                    </button>
                    <button
                      type="button"
                      className="btn"
                      style={{
                        fontSize: 12,
                        padding: "5px 14px",
                        height: "auto",
                        background: "var(--primary-subtle)",
                        color: "var(--primary)",
                        borderColor: "var(--primary-border)",
                        fontWeight: 600,
                      }}
                      disabled={loading}
                      onClick={() => executeIngest(uploadTitle, uploadText || voiceTranscript)}
                    >
                      <Sparkles size={13} style={{ marginRight: 4 }} /> ⚡ Analyze Voice Note Now
                    </button>
                  </div>
                )}
              </div>
            )}

            <label>Upload a file</label>
            <label className="dropzone">
              <input
                type="file"
                accept=".txt,.md,.csv,.pdf,.mp3,.wav,.m4a"
                onChange={(e) => ingestFile(e.target.files?.[0])}
              />
              <UploadCloud size={26} />
              <b>Choose a file</b>
              <span>PDF, TXT, Markdown, CSV, Audio · Max 10 MB</span>
              <small>Uploaded content is treated as untrusted input.</small>
            </label>

            <div className="or">OR PASTE TEXT</div>
            <label>Source title</label>
            <input
              className="input"
              value={uploadTitle}
              onChange={(e) => setUploadTitle(e.target.value)}
            />
            <label>Meeting notes / email content</label>
            <textarea
              className="input"
              rows={6}
              value={uploadText}
              onChange={(e) => setUploadText(e.target.value)}
              placeholder={
                "Paste unstructured notes here...\nExample: Action: Priya must send the launch plan by 2026-11-02."
              }
            />

            <div className="modalfoot">
              <span>
                <ShieldCheck size={14} /> Evidence-linked extraction
              </span>
              <button
                className="primary"
                disabled={!uploadText.trim() || loading}
                onClick={ingestText}
              >
                {loading ? <LoaderCircle className="spin" /> : <Sparkles size={16} />} Analyze source
              </button>
            </div>
          </section>
        </div>
      )}

      {/* Drawer: Task inspection & edit with Feature 3 Evidence Inspector & Feature 4 Conflict Box */}
      {selected && (
        <div
          className="backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setSelected(null);
          }}
        >
          <aside className="drawer">
            <div className="drawerhead">
              <div>
                <div className="eyebrow">TASK DETAILS</div>
                <h2>Review proposal</h2>
              </div>
              <button className="iconbtn" onClick={() => setSelected(null)}>
                <X />
              </button>
            </div>
            <div className="drawerbadges">
              <Badge
                tone={
                  selected.status === "approved"
                    ? "green"
                    : selected.status === "rejected"
                    ? "red"
                    : "amber"
                }
              >
                {selected.status}
              </Badge>
              <Badge>{selected.priority} priority</Badge>
              {selected.dispatched ? (
                <span className="dispatch-pill">
                  <CheckCircle2 size={11} /> Dispatched ({selected.dispatch_channel})
                </span>
              ) : null}
              <span>{Math.round(selected.confidence * 100)}% confidence</span>
            </div>

            <div className="drawerscroll">
              {/* Feature 4: AI Conflict Resolver Box inside Drawer */}
              {selected.uncertainty_flags.some((f) => f.toLowerCase().includes("conflict")) && (
                <div className="conflict-resolver-box">
                  <h4>
                    <AlertTriangle size={15} /> Deadline Conflict Flagged by ActionPilot
                  </h4>
                  <p>
                    {selected.uncertainty_flags.find((f) => f.toLowerCase().includes("conflict"))}
                  </p>
                  <div className="conflict-dates-row">
                    <div className="conflict-date-badge">
                      <span>Original Date:</span>
                      <b>{dateLabel(selected.due_date)}</b>
                    </div>
                    <div className="conflict-date-badge" style={{ borderColor: "#ef4444" }}>
                      <span>Client / Later Instruction:</span>
                      <b>Nov 6, 2026 (Recommended)</b>
                    </div>
                  </div>
                  <div className="conflict-actions-row">
                    <button
                      className="conflict-resolve-btn"
                      onClick={() =>
                        resolveTaskConflict(
                          selected,
                          "2026-11-06",
                          "Adopted later date per client update note"
                        )
                      }
                    >
                      <Zap size={13} /> Adopt 2026-11-06 (Client Date)
                    </button>
                    <button
                      className="conflict-keep-btn"
                      onClick={() =>
                        resolveTaskConflict(
                          selected,
                          selected.due_date || "2026-11-02",
                          "Retained internal initial date"
                        )
                      }
                    >
                      Retain {selected.due_date}
                    </button>
                  </div>
                </div>
              )}

              <label>Task title</label>
              <input
                className="input"
                disabled={selected.status === "approved"}
                value={edit.title}
                onChange={(e) => setEdit({ ...edit, title: e.target.value })}
              />
              <label>Description</label>
              <textarea
                className="input"
                rows={3}
                disabled={selected.status === "approved"}
                value={edit.description}
                onChange={(e) => setEdit({ ...edit, description: e.target.value })}
              />
              <div className="two">
                <div>
                  <label>Assignee</label>
                  <input
                    className="input"
                    disabled={selected.status === "approved"}
                    value={edit.assignee}
                    onChange={(e) => setEdit({ ...edit, assignee: e.target.value })}
                    placeholder="Unassigned"
                  />
                </div>
                <div>
                  <label>Due date</label>
                  <input
                    className="input"
                    type="date"
                    disabled={selected.status === "approved"}
                    value={edit.due_date}
                    onChange={(e) => setEdit({ ...edit, due_date: e.target.value })}
                  />
                </div>
              </div>
              <label>Priority</label>
              <select
                className="input"
                disabled={selected.status === "approved"}
                value={edit.priority}
                onChange={(e) => setEdit({ ...edit, priority: e.target.value })}
              >
                <option>low</option>
                <option>medium</option>
                <option>high</option>
                <option>urgent</option>
              </select>

              {/* Feature 3: Interactive Evidence Excerpt with "View in Source" button */}
              <div className="subhead">
                <FileText size={16} /> Source evidence <Badge>{selected.evidence.length} excerpts</Badge>
              </div>
              {selected.evidence.map((e, i) => (
                <div className="evidence" key={i}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <small>
                      {e.source_name} · characters {e.start}–{e.end}
                    </small>
                    <button
                      className="evidence-inspector-btn"
                      onClick={() => openSourceContext(selected.document_id, e.quote)}
                      title="Inspect highlight in original source"
                    >
                      <Sparkles size={12} /> View in Context ↗
                    </button>
                  </div>
                  <p>“{e.quote}”</p>
                  <span>✓ Immutable Source Evidence Linked</span>
                </div>
              ))}

              {selected.uncertainty_flags.length > 0 && (
                <>
                  <div className="subhead">
                    <AlertTriangle size={16} /> Review flags{" "}
                    <Badge tone="amber">{selected.uncertainty_flags.length}</Badge>
                  </div>
                  {selected.uncertainty_flags.map((f, i) => (
                    <div className="warning" key={i}>
                      <AlertTriangle size={15} />
                      {f}
                    </div>
                  ))}
                </>
              )}

              <div className="safetynote">
                <ShieldCheck size={16} /> Human approval required before external dispatch.
              </div>
            </div>

            <div className="drawerfoot">
              {selected.status === "proposed" && (
                <>
                  <button className="secondary" onClick={saveTask}>
                    Save edits
                  </button>
                  <button className="danger" onClick={() => taskAction(selected.id, "reject")}>
                    Reject
                  </button>
                  <button className="primary" onClick={() => taskAction(selected.id, "approve")}>
                    <Check size={15} /> Approve
                  </button>
                </>
              )}
              {selected.status === "approved" && (
                <button
                  className="primary full"
                  onClick={() => openDispatchModal(selected)}
                >
                  <Zap size={15} /> Dispatch Action (Calendar / Slack / GitHub)
                </button>
              )}
            </div>
          </aside>
        </div>
      )}

      {/* Feature 3 Modal: Source Context Inspector with Radiant Yellow Highlight */}
      {sourceInspectorOpen && sourceDocText && (
        <div
          className="backdrop top"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setSourceInspectorOpen(false);
          }}
        >
          <section className="modal" style={{ width: "min(680px, 100%)" }}>
            <div className="modalhead">
              <div>
                <div className="eyebrow">
                  <Sparkles size={13} /> EVIDENCE TRACEABILITY
                </div>
                <h2>Source Text Inspector</h2>
                <p>
                  Document: <b>{sourceDocText.title}</b>
                </p>
              </div>
              <button className="iconbtn" onClick={() => setSourceInspectorOpen(false)}>
                <X />
              </button>
            </div>

            <div className="source-inspector-head">
              <span>● Grounded Source Content</span>
              <span>Highlighted in amber: Exact quote linked by AI</span>
            </div>

            <div className="source-inspector-card">
              {renderHighlightedText(sourceDocText.content, targetHighlight)}
            </div>

            <div className="modalfoot">
              <span style={{ color: "#eab308" }}>
                <CheckCircle2 size={14} /> Zero Hallucination: Verifiable offset
              </span>
              <button className="secondary" onClick={() => setSourceInspectorOpen(false)}>
                Close Inspector
              </button>
            </div>
          </section>
        </div>
      )}

      {/* Feature 4 Modal: Quick AI Conflict Resolver popup */}
      {conflictModalTask && (
        <div
          className="backdrop top"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setConflictModalTask(null);
          }}
        >
          <section className="modal">
            <div className="modalhead">
              <div>
                <div className="eyebrow" style={{ color: "#ef4444" }}>
                  <AlertTriangle size={13} /> CONFLICT DETECTED
                </div>
                <h2>Discrepancy Resolution</h2>
                <p>Task: "{conflictModalTask.title}"</p>
              </div>
              <button className="iconbtn" onClick={() => setConflictModalTask(null)}>
                <X />
              </button>
            </div>

            <div className="conflict-resolver-box">
              <p>
                Two contradictory deadlines were extracted for this action item:
              </p>
              <div className="conflict-dates-row">
                <div className="conflict-date-badge">
                  <span>Initial Meeting Note:</span>
                  <b>{dateLabel(conflictModalTask.due_date)}</b>
                </div>
                <div className="conflict-date-badge" style={{ borderColor: "rgba(239, 68, 68, 0.5)", background: "rgba(239, 68, 68, 0.1)" }}>
                  <span>Client Confirmation:</span>
                  <b>Nov 6, 2026 (Superseding)</b>
                </div>
              </div>
              <p style={{ fontSize: 12, color: "#cbd5e1", margin: 0, lineHeight: 1.5 }}>
                💡 <b>Resolution Note:</b> Client confirmations supersede earlier internal drafts. Recommend adopting <b>2026-11-06</b>.
              </p>
            </div>

            <div className="modalfoot">
              <button className="secondary" onClick={() => setConflictModalTask(null)}>
                Cancel
              </button>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  className="secondary"
                  onClick={() =>
                    resolveTaskConflict(
                      conflictModalTask,
                      conflictModalTask.due_date || "2026-11-02",
                      "Retained initial internal date"
                    )
                  }
                >
                  Keep {conflictModalTask.due_date}
                </button>
                <button
                  className="primary"
                  style={{ background: "#ef4444", borderColor: "#dc2626" }}
                  onClick={() =>
                    resolveTaskConflict(
                      conflictModalTask,
                      "2026-11-06",
                      "Adopted client confirmed date per ActionPilot resolution"
                    )
                  }
                >
                  <Zap size={14} /> Adopt 2026-11-06
                </button>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* Feature 5 Modal: One-Click Action Dispatcher (Google Calendar / Slack / GitHub / Email) */}
      {dispatchModalOpen && dispatchTask && (
        <div
          className="backdrop top"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setDispatchModalOpen(false);
          }}
        >
          <section className="modal" style={{ width: "min(560px, 100%)" }}>
            <div className="modalhead">
              <div>
                <div className="eyebrow" style={{ color: "#6366f1" }}>
                  <Zap size={13} /> EXTERNAL INTEGRATION
                </div>
                <h2>Dispatch Approved Action</h2>
                <p>Task: "{dispatchTask.title}"</p>
              </div>
              <button className="iconbtn" onClick={() => setDispatchModalOpen(false)}>
                <X />
              </button>
            </div>

            {/* Integration Target Tabs */}
            <div className="dispatch-channel-tabs">
              <button
                type="button"
                className={"dispatch-channel-tab " + (dispatchChannel === "calendar" ? "active" : "")}
                onClick={() => {
                  setDispatchChannel("calendar");
                  setDispatchFeedback(null);
                }}
              >
                <Calendar />
                <span>Google Calendar</span>
              </button>
              <button
                type="button"
                className={"dispatch-channel-tab " + (dispatchChannel === "slack" ? "active" : "")}
                onClick={() => {
                  setDispatchChannel("slack");
                  setDispatchFeedback(null);
                }}
              >
                <Slack />
                <span>Slack Webhook</span>
              </button>
              <button
                type="button"
                className={"dispatch-channel-tab " + (dispatchChannel === "github" ? "active" : "")}
                onClick={() => {
                  setDispatchChannel("github");
                  setDispatchFeedback(null);
                }}
              >
                <Github />
                <span>GitHub Issue</span>
              </button>
              <button
                type="button"
                className={"dispatch-channel-tab " + (dispatchChannel === "email" ? "active" : "")}
                onClick={() => {
                  setDispatchChannel("email");
                  setDispatchFeedback(null);
                }}
              >
                <Mail />
                <span>Email Notice</span>
              </button>
            </div>

            {dispatchChannel === "calendar" && (
              <div>
                <p style={{ fontSize: 11, color: "#64748b", margin: "0 0 10px" }}>
                  Creates an event on Google Calendar scheduled for <b>{dateLabel(dispatchTask.due_date)}</b> with pre-filled description and evidence.
                </p>
                {dispatchFeedback?.calendar_url && (
                  <div className="dispatch-preview-card">
                    <p style={{ margin: "0 0 8px", color: "#15803d", fontWeight: 700 }}>
                      ✓ Google Calendar Event Ready:
                    </p>
                    <a
                      href={dispatchFeedback.calendar_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="primary"
                      style={{ textDecoration: "none", display: "inline-flex" }}
                    >
                      <Calendar size={14} /> Open in Google Calendar <ExternalLink size={13} />
                    </a>
                  </div>
                )}
              </div>
            )}

            {dispatchChannel === "slack" && (
              <div>
                <label>Slack / Discord Webhook URL (Optional)</label>
                <input
                  className="input"
                  placeholder="https://hooks.slack.com/services/..."
                  value={dispatchTarget}
                  onChange={(e) => setDispatchTarget(e.target.value)}
                />
                <p style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                  Leave empty to execute a simulated dry-run delivery.
                </p>
              </div>
            )}

            {dispatchChannel === "github" && (
              <div>
                <label>GitHub Repository (owner/repo)</label>
                <input
                  className="input"
                  placeholder="my-team/actionpilot-project"
                  value={dispatchTarget}
                  onChange={(e) => setDispatchTarget(e.target.value)}
                />
                {dispatchFeedback?.github_url && (
                  <div className="dispatch-preview-card">
                    <p style={{ margin: "0 0 8px", color: "#15803d", fontWeight: 700 }}>
                      ✓ Pre-filled Issue Ready:
                    </p>
                    <a
                      href={dispatchFeedback.github_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="primary"
                      style={{ textDecoration: "none", display: "inline-flex" }}
                    >
                      <Github size={14} /> Create Issue on GitHub <ExternalLink size={13} />
                    </a>
                  </div>
                )}
              </div>
            )}

            {dispatchChannel === "email" && (
              <div>
                <label>Recipient Email Address</label>
                <input
                  className="input"
                  placeholder="assignee@company.com"
                  value={dispatchTarget}
                  onChange={(e) => setDispatchTarget(e.target.value)}
                />
              </div>
            )}

            {/* Dry-Run Simulation Toggle */}
            <label className="simulation-toggle">
              <input
                type="checkbox"
                checked={dispatchSimulate}
                onChange={(e) => setDispatchSimulate(e.target.checked)}
              />
              <span>
                <b>Dry-run simulation mode</b> (Recommended for live demos — validates payload without external network dependencies)
              </span>
            </label>

            <div className="modalfoot">
              <button className="secondary" onClick={() => setDispatchModalOpen(false)}>
                Done
              </button>
              <button
                className="primary"
                disabled={dispatchLoading}
                onClick={handleExecuteDispatch}
              >
                {dispatchLoading ? <LoaderCircle size={15} className="spin" /> : <Zap size={15} />}
                Execute Dispatch Now
              </button>
            </div>
          </section>
        </div>
      )}

      {toast && (
        <div className="toast">
          <Check size={15} />
          {toast}
        </div>
      )}
    </div>
  );
}

function Empty({
  title,
  text,
  action,
  btnText = "Add source",
  secondaryAction,
  secondaryBtnText,
  icon: Icon = Inbox,
}: {
  title: string;
  text: string;
  action?: () => void;
  btnText?: string;
  secondaryAction?: () => void;
  secondaryBtnText?: string;
  icon?: any;
}) {
  return (
    <div className="empty">
      <div className="empty-icon-wrap">
        <Icon size={24} />
      </div>
      <b>{title}</b>
      <p>{text}</p>
      <div className="empty-actions">
        {action && (
          <button className="primary" onClick={action}>
            <Plus size={14} /> {btnText}
          </button>
        )}
        {secondaryAction && (
          <button className="secondary" onClick={secondaryAction}>
            <Zap size={14} /> {secondaryBtnText}
          </button>
        )}
      </div>
    </div>
  );
}

function TaskCard({
  t,
  open,
  approve,
  reject,
  onResolveConflict,
  onOpenSource,
  onDispatch,
}: {
  t: Task;
  open: () => void;
  approve: () => void;
  reject: () => void;
  onResolveConflict?: () => void;
  onOpenSource?: (quote: string) => void;
  onDispatch?: () => void;
}) {
  const hasConflict = t.uncertainty_flags.some((f) => f.toLowerCase().includes("conflict"));
  const firstQuote = t.evidence?.[0]?.quote || "";

  return (
    <article className="taskcard">
      <div className="tasktop">
        <div className="taskglyph">
          <ListTodo size={18} />
        </div>
        <div className="taskbody">
          <button className="tasktitle" onClick={open}>
            {t.title}
          </button>
          <p>{t.description}</p>
          <div className="taskmeta">
            <span>◉ {t.assignee || "Unassigned"}</span>
            <span>
              <Clock3 size={13} />
              {dateLabel(t.due_date)}
            </span>
            <span>
              <FileText size={13} />
              {t.evidence.length} evidence
            </span>
            {t.dispatched ? (
              <span style={{ color: "#059669", fontWeight: 700 }}>
                <CheckCircle2 size={12} /> Dispatched ({t.dispatch_channel})
              </span>
            ) : null}
          </div>
        </div>
        <div className="taskside">
          <Badge tone={t.status === "approved" ? "green" : t.status === "rejected" ? "red" : "amber"}>
            {t.status}
          </Badge>
          <Badge>{t.priority}</Badge>
          <small>{Math.round(t.confidence * 100)}% confidence</small>
        </div>
      </div>

      {/* Conflict Flag Card with 1-click Resolve trigger */}
      {hasConflict && (
        <div
          className="taskflag"
          style={{
            background: "rgba(239, 68, 68, 0.08)",
            borderColor: "rgba(239, 68, 68, 0.3)",
            color: "#fca5a5",
          }}
        >
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{t.uncertainty_flags.find((f) => f.toLowerCase().includes("conflict"))}</span>
          <button
            onClick={onResolveConflict}
            style={{
              background: "#ef4444",
              color: "#fff",
              padding: "4px 9px",
              borderRadius: 6,
              fontWeight: 600,
            }}
          >
            Resolve Conflict
          </button>
        </div>
      )}

      {/* Non-conflict warning flags */}
      {!hasConflict && !!t.uncertainty_flags.length && (
        <div className="taskflag">
          <AlertTriangle size={14} />
          <span>
            {t.uncertainty_flags.length} review flag(s) — {t.uncertainty_flags[0]}
          </span>
          <button onClick={open}>Inspect ↗</button>
        </div>
      )}

      <div className="taskfoot">
        <div style={{ display: "flex", gap: 10 }}>
          <button className="subtle" onClick={open}>
            Review details ↗
          </button>
          {firstQuote && onOpenSource && (
            <button
              className="evidence-inspector-btn"
              onClick={() => onOpenSource(firstQuote)}
              title="Highlight quote in source text"
            >
              <Sparkles size={12} /> View in Source Context
            </button>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {t.status === "proposed" && (
            <div className="actions">
              <button className="dangertext" onClick={reject}>
                Reject
              </button>
              <button className="approve" onClick={approve}>
                <Check size={14} /> Approve
              </button>
            </div>
          )}
          {t.status === "approved" && (
            <>
              <span className="approved">
                <CheckCheck size={15} /> Approved
              </span>
              <button
                className="primary"
                style={{
                  padding: "6px 12px",
                  fontSize: 12,
                }}
                onClick={onDispatch}
              >
                <Zap size={13} /> Dispatch Action
              </button>
            </>
          )}
        </div>
      </div>
    </article>
  );
}

function AuditRow({ a, detailed = false }: { a: Audit; detailed?: boolean }) {
  return (
    <div className="auditrow">
      <div className="auditglyph">
        <Activity size={15} />
      </div>
      <div className="auditcopy">
        <b>{a.event_type.replaceAll("_", " ")}</b>
        <small>
          {a.entity_type} · {a.entity_id.slice(0, 8)} · {a.actor}
        </small>
        {detailed && <pre>{JSON.stringify(a.details, null, 2)}</pre>}
      </div>
      <time>{timeLabel(a.created_at)}</time>
    </div>
  );
}

import { useEffect, useRef, useState, useCallback } from "react";
import {
  Send,
  Upload,
  FileText,
  Trash2,
  LogOut,
  User,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  ChevronRight,
  GitCompare,
  MessageSquare,
  Search,
  AlertCircle,
  XCircle,
  Info,
  Eye,
  BookOpen,
  Sparkles,
  CheckCircle2,
  Zap,
  FileSearch,
  ArrowRight,
  HelpCircle,
  Layers,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

/* ================================================================
   HELPERS
   ================================================================ */
function getToken() {
  return localStorage.getItem("rag_token");
}
function setToken(token) {
  localStorage.setItem("rag_token", token);
}
function clearToken() {
  localStorage.removeItem("rag_token");
  localStorage.removeItem("rag_user");
}
function getUser() {
  try {
    return JSON.parse(localStorage.getItem("rag_user"));
  } catch {
    return null;
  }
}
function setUser(u) {
  localStorage.setItem("rag_user", JSON.stringify(u));
}
function authHeaders(extra = {}) {
  const token = getToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

/** Get the faithfulness level label. */
function faithLevel(score) {
  if (score < 0) return "unknown";
  if (score >= 0.8) return "high";
  if (score >= 0.5) return "medium";
  return "low";
}

/** Find a citation verdict for a given citation number. */
function findVerdict(verdicts, n) {
  if (!verdicts?.length) return null;
  return verdicts.find((v) => v.citation_number === n) || null;
}

/** Render answer text, turning [n] markers into clickable citation chips. */
function renderAnswer(text, citations = [], verdicts = [], onCite) {
  const parts = text.split(/(\[[A-B]?\d+\])/g);
  return parts.map((p, i) => {
    const m = p.match(/^\[([A-B]?\d+)\]$/);
    if (m) {
      const label = m[1];
      
      // Check if this citation actually exists in the data
      const citationExists = citations.some((x) => String(x.n) === String(label));
      
      if (citationExists) {
        const numOnly = parseInt(label.replace(/[AB]/, ""), 10);
        const verdict = findVerdict(verdicts, numOnly);
        let cls = "cite";
        if (verdict) {
          cls += verdict.supported ? " verified" : " unsupported";
        }
        return (
          <button key={i} className={cls} onClick={() => onCite(label)}>
            {p}
          </button>
        );
      }
    }
    return <span key={i}>{p}</span>;
  });
}

/* ================================================================
   AUTH SCREEN
   ================================================================ */
function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const endpoint =
        mode === "register" ? "/auth/register" : "/auth/login";
      const body =
        mode === "register"
          ? { email, password, name }
          : { email, password };
      const r = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Auth failed");
      setToken(data.access_token);
      setUser({ id: data.user_id, name: data.name, email: data.email });
      onAuth();
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const features = [
    {
      icon: <Upload size={20} />,
      title: "Upload Documents",
      desc: "Drop in your PDFs and we'll chunk, embed, and index them automatically.",
    },
    {
      icon: <MessageSquare size={20} />,
      title: "Ask Questions",
      desc: "Chat naturally and get AI answers grounded in your own documents.",
    },
    {
      icon: <ShieldCheck size={20} />,
      title: "Verified Citations",
      desc: "Every claim is traced back to source text with faithfulness scoring.",
    },
    {
      icon: <GitCompare size={20} />,
      title: "Compare Documents",
      desc: "Select two documents and compare their content side by side.",
    },
  ];

  return (
    <div className="auth-wrapper">
      {/* Left hero panel */}
      <div className="auth-hero">
        <div className="auth-hero-content">
          <div className="auth-hero-badge">
            <Sparkles size={14} />
            AI-Powered Knowledge
          </div>
          <h1 className="auth-hero-title">
            RAG Knowledge<br />Assistant
          </h1>
          <p className="auth-hero-subtitle">
            Upload your documents, ask questions in plain language, and get
            AI-generated answers backed by verifiable citations. Every
            response is grounded in your own data.
          </p>
          <div className="auth-features-grid">
            {features.map((f, i) => (
              <div key={i} className="auth-feature-card" style={{ animationDelay: `${i * 0.1}s` }}>
                <div className="auth-feature-icon">{f.icon}</div>
                <div>
                  <div className="auth-feature-title">{f.title}</div>
                  <div className="auth-feature-desc">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="auth-form-panel">
        <form className="auth-card" onSubmit={submit}>
          <div className="auth-card-header">
            <div className="auth-logo-mark">
              <BookOpen size={22} />
            </div>
            <h2>{mode === "login" ? "Welcome back" : "Get started"}</h2>
            <p className="subtitle">
              {mode === "login"
                ? "Sign in to access your knowledge base"
                : "Create an account to start building your knowledge base"}
            </p>
          </div>

          {mode === "register" && (
            <>
              <label htmlFor="auth-name">Name</label>
              <input
                id="auth-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                required
              />
            </>
          )}

          <label htmlFor="auth-email">Email</label>
          <input
            id="auth-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />

          <label htmlFor="auth-password">Password</label>
          <input
            id="auth-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            minLength={6}
            required
          />

          <button
            type="submit"
            className="auth-btn"
            disabled={loading}
          >
            {loading
              ? "Please wait…"
              : mode === "login"
              ? "Sign In"
              : "Create Account"}
            {!loading && <ArrowRight size={16} />}
          </button>

          {error && <div className="auth-error">{error}</div>}

          <p className="switch-link">
            {mode === "login" ? (
              <>
                Don't have an account?{" "}
                <button type="button" onClick={() => { setMode("register"); setError(""); }}>
                  Register
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button type="button" onClick={() => { setMode("login"); setError(""); }}>
                  Sign in
                </button>
              </>
            )}
          </p>
        </form>
      </div>
    </div>
  );
}

/* ================================================================
   MAIN APP
   ================================================================ */
export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [user, setUserState] = useState(getUser());

  if (!authed) {
    return (
      <AuthScreen
        onAuth={() => {
          setAuthed(true);
          setUserState(getUser());
        }}
      />
    );
  }

  return (
    <MainLayout
      user={user}
      onLogout={() => {
        clearToken();
        setAuthed(false);
        setUserState(null);
      }}
    />
  );
}

/* ================================================================
   MAIN LAYOUT
   ================================================================ */
function MainLayout({ user, onLogout }) {
  const [docs, setDocs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeCite, setActiveCite] = useState(null);
  const [activeFaithfulness, setActiveFaithfulness] = useState(null);
  const [overviewDoc, setOverviewDoc] = useState(null);
  const [uploadMsg, setUploadMsg] = useState("");
  const [mode, setMode] = useState("chat"); // "chat" | "compare"
  const [selectedDocs, setSelectedDocs] = useState([]);
  const fileRef = useRef(null);
  const bottomRef = useRef(null);

  const refreshDocs = useCallback(async () => {
    try {
      const r = await fetch(`${API}/documents`, {
        headers: authHeaders(),
      });
      if (r.status === 401) {
        clearToken();
        window.location.reload();
        return;
      }
      setDocs(await r.json());
    } catch {
      /* backend not up yet */
    }
  }, []);

  useEffect(() => {
    refreshDocs();
  }, [refreshDocs]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const upload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadMsg("Uploading & ingesting…");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await fetch(`${API}/documents`, {
        method: "POST",
        headers: authHeaders(),
        body: fd,
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "upload failed");
      setUploadMsg(`✓ ${data.name}: ${data.chunks} chunks indexed`);
      refreshDocs();
    } catch (err) {
      setUploadMsg(`✗ ${err.message}`);
    }
    fileRef.current.value = "";
  };

  const deleteDoc = async (docId) => {
    try {
      await fetch(`${API}/documents/${docId}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      refreshDocs();
      setSelectedDocs((s) => s.filter((id) => id !== docId));
    } catch {
      /* ignore */
    }
  };

  const toggleDocSelection = (docId) => {
    setSelectedDocs((prev) => {
      if (prev.includes(docId)) return prev.filter((id) => id !== docId);
      if (prev.length >= 2) return [prev[1], docId]; // keep last 2
      return [...prev, docId];
    });
  };

  const ask = async (e) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;
    setQuestion("");
    setActiveCite(null);
    setActiveFaithfulness(null);
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      if (mode === "compare" && selectedDocs.length === 2) {
        // Multi-doc comparison
        const r = await fetch(`${API}/compare`, {
          method: "POST",
          headers: authHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({
            question: q,
            doc_ids: selectedDocs,
            top_k_per_doc: 3,
            rerank: true,
          }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || "compare failed");
        // Merge citations from both docs
        const allCitations = [
          ...(data.doc_a?.citations || []),
          ...(data.doc_b?.citations || []),
        ];
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            text: data.answer,
            citations: allCitations,
            faithfulness: data.faithfulness,
            isComparison: true,
            docA: data.doc_a,
            docB: data.doc_b,
          },
        ]);
      } else {
        // Normal query
        const payload = { question: q, top_k: 5, rerank: true };
        if (selectedDocs.length > 0) payload.doc_ids = selectedDocs;

        const r = await fetch(`${API}/query`, {
          method: "POST",
          headers: authHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify(payload),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || "query failed");
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            text: data.answer,
            citations: data.citations,
            faithfulness: data.faithfulness,
          },
        ]);
      }
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Error: ${err.message}`, citations: [] },
      ]);
    }
    setLoading(false);
  };

  // Find the last message with citations for the sources panel
  const lastAssistant = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && m.citations?.length);

  return (
    <div className="layout">
      {/* ── NARROW ICON SIDEBAR ─────────────────────────────── */}
      <nav className="sidebar-icons">
        <div className="icon-group">
          <div className="app-logo">
            <BookOpen size={18} />
          </div>
        </div>
        <div className="icon-group center">
          <button
            className={`icon-btn ${mode === 'chat' ? 'active' : ''}`}
            title="Chat — ask questions about your documents"
            onClick={() => setMode('chat')}
          >
            <MessageSquare size={18} />
            <span className="icon-tooltip">Chat</span>
          </button>
          <button
            className={`icon-btn ${mode === 'compare' ? 'active' : ''}`}
            title="Compare — analyze differences between two documents"
            onClick={() => setMode('compare')}
          >
            <GitCompare size={18} />
            <span className="icon-tooltip">Compare</span>
          </button>
        </div>
        <div className="icon-group bottom">
          <div className="user-avatar-sidebar" title={user?.email || "User"}>
            {user?.name?.charAt(0)?.toUpperCase() || <User size={14} />}
          </div>
          <button className="icon-btn" title="Sign out" onClick={onLogout}>
            <LogOut size={18} />
            <span className="icon-tooltip">Sign out</span>
          </button>
        </div>
      </nav>

      {/* ── SECONDARY SIDEBAR ───────────────────────────────── */}
      <aside className="sidebar-secondary">
        {/* Mode context */}
        <div className="sidebar-mode-info">
          {mode === "chat" ? (
            <>
              <div className="mode-info-header">
                <MessageSquare size={16} />
                <span>Chat Mode</span>
              </div>
              <p className="mode-info-desc">
                Ask questions about your uploaded documents. Select specific documents to narrow the search, or leave all unchecked to search everything.
              </p>
            </>
          ) : (
            <>
              <div className="mode-info-header">
                <GitCompare size={16} />
                <span>Compare Mode</span>
              </div>
              <p className="mode-info-desc">
                Select exactly <strong>2 documents</strong> below, then ask a question to compare their content side by side.
              </p>
              {selectedDocs.length < 2 && (
                <div className="mode-info-hint">
                  <Info size={12} />
                  {selectedDocs.length === 0
                    ? "Select 2 documents to begin"
                    : "Select 1 more document"}
                </div>
              )}
            </>
          )}
        </div>

        <div className="documents-section">
          <h3 className="section-title">
            <FileText size={12} />
            Your Documents
            {docs.length > 0 && <span className="doc-count">{docs.length}</span>}
          </h3>
          <label className="upload-btn-light">
            <Upload size={14} /> Upload PDF
            <input ref={fileRef} type="file" accept=".pdf" hidden onChange={upload} />
          </label>
          {uploadMsg && <div className="upload-msg-light">{uploadMsg}</div>}
          
          {docs.length === 0 ? (
            <div className="docs-empty-state">
              <Layers size={32} />
              <p>No documents yet</p>
              <span>Upload a PDF to get started</span>
            </div>
          ) : (
            <ul className="doc-list-light">
              {docs.map((d) => (
                <li key={d.doc_id} className={`doc-item-light ${selectedDocs.includes(d.doc_id) ? "selected" : ""}`} onClick={() => toggleDocSelection(d.doc_id)}>
                  <input type="checkbox" checked={selectedDocs.includes(d.doc_id)} readOnly style={{ marginRight: 8 }} />
                  <span className="doc-name-light" title={d.name}>{d.name}</span>
                  <button className="del-btn" title="View PDF" onClick={(e) => { e.stopPropagation(); setOverviewDoc({ id: d.doc_id, name: d.name }); }}><Eye size={12} /></button>
                  <button className="del-btn" title="Delete" onClick={(e) => { e.stopPropagation(); deleteDoc(d.doc_id); }}><Trash2 size={12} /></button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      {/* ── CHAT ────────────────────────────────────────────── */}
      <main className="chat">
        <div className="top-bar">
          <div className="top-bar-left">
            <h1 className="app-title">RAG Knowledge Assistant</h1>
          </div>
          <div className="top-bar-right">
            <div className="current-mode-label">
              {mode === 'chat' ? <MessageSquare size={14} /> : <GitCompare size={14} />}
              {mode === 'chat' ? 'Chat Mode' : 'Compare Mode'}
            </div>
            <div className="user-greeting">
              Hi, {user?.name || "there"}
            </div>
          </div>
        </div>
        <div className="messages">
          {messages.length === 0 && (
            <OnboardingEmpty user={user} mode={mode} hasDocs={docs.length > 0} />
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              {m.role === "assistant" && (
                <div className="assistant-avatar-wrapper">
                  <div className="agent-avatar">
                    <Sparkles size={16} />
                  </div>
                  <span className="avatar-label">Agent</span>
                </div>
              )}
              <div className="bubble">
                {m.role === "assistant" ? (
                  <>
                    {renderAnswer(
                      m.text,
                      m.citations || [],
                      m.faithfulness?.citation_verdicts || [],
                      (label) => {
                        const cites = m.citations || [];
                        const c = cites.find((x) => String(x.n) === String(label));
                        if (c) { setActiveCite(c); setActiveFaithfulness(m.faithfulness); }
                      }
                    )}
                    {m.citations && m.citations.length > 0 && m.faithfulness && m.faithfulness.faithfulness_score >= 0 && (
                      <FaithfulnessBadge score={m.faithfulness.faithfulness_score} />
                    )}
                  </>
                ) : (
                  m.text
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="msg assistant">
              <div className="assistant-avatar-wrapper">
                <div className="agent-avatar">
                  <Sparkles size={16} />
                </div>
                <span className="avatar-label">Agent</span>
              </div>
              <div className="bubble thinking">
                Searching & generating<span className="thinking-dots"><span></span><span></span><span></span></span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form className="composer-container" onSubmit={ask}>
          <div className="composer">
            <button type="button" className="composer-plus" title="Upload a document" onClick={() => fileRef.current?.click()}>+</button>
            <input
              id="question-input"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                mode === "compare" && selectedDocs.length !== 2
                  ? "Select 2 documents to compare…"
                  : mode === "compare"
                  ? "Ask a comparison question…"
                  : "Ask a question about your documents…"
              }
              disabled={loading || (mode === "compare" && selectedDocs.length !== 2)}
            />
            <button type="submit" disabled={loading || !question.trim()} className="composer-send">
              <Send size={18} />
            </button>
          </div>
          <p className="composer-hint">
            {mode === "chat"
              ? "Answers include citations you can click to verify against source text"
              : "Comparing documents highlights similarities and differences"}
          </p>
        </form>
      </main>

      {/* ── SOURCES PANEL ───────────────────────────────────── */}
      <aside className={`sources ${activeCite ? "open" : ""}`}>
        <div className="sources-header">
          <h2>
            <FileSearch size={14} />
            Source Inspector
          </h2>
          <button className="close-source-btn" onClick={() => setActiveCite(null)}><XCircle size={16} /></button>
        </div>
        <div className="sources-body">
          {activeCite ? (
            <SourceDetail cite={activeCite} faithfulness={activeFaithfulness} allCitations={lastAssistant?.citations || []} onSelect={(c) => setActiveCite(c)} />
          ) : (
            <div className="sources-empty">
              <FileSearch size={40} />
              <h3>No source selected</h3>
              <p>Click on a <span className="inline-cite-example">[1]</span> citation in any answer to inspect its source text and verify the claim.</p>
              <div className="sources-legend">
                <div className="legend-item">
                  <span className="legend-dot verified"></span>
                  Verified — claim is supported
                </div>
                <div className="legend-item">
                  <span className="legend-dot unsupported"></span>
                  Unsupported — needs review
                </div>
                <div className="legend-item">
                  <span className="legend-dot unknown"></span>
                  Unknown — no verdict yet
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* ── PDF OVERVIEW MODAL ─────────────────────────────── */}
      {overviewDoc && (
        <div className="pdf-modal-overlay" onClick={() => setOverviewDoc(null)}>
          <div className="pdf-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="pdf-modal-header">
              <h3>
                <FileText size={16} />
                {overviewDoc.name}
              </h3>
              <button className="close-source-btn" onClick={() => setOverviewDoc(null)}><XCircle size={18} /></button>
            </div>
            <iframe src={`${API}/uploads/${overviewDoc.id}.pdf`} title={overviewDoc.name} className="pdf-iframe" />
          </div>
        </div>
      )}
    </div>
  );
}

/* ================================================================
   ONBOARDING EMPTY STATE
   ================================================================ */
function OnboardingEmpty({ user, mode, hasDocs }) {
  const steps = mode === "chat"
    ? [
        {
          icon: <Upload size={22} />,
          num: "1",
          title: "Upload Documents",
          desc: "Add PDF files using the sidebar. They'll be chunked and embedded automatically.",
          done: hasDocs,
        },
        {
          icon: <Search size={22} />,
          num: "2",
          title: "Ask Questions",
          desc: "Type a question below — the AI searches your documents for relevant passages.",
          done: false,
        },
        {
          icon: <ShieldCheck size={22} />,
          num: "3",
          title: "Verify Sources",
          desc: "Click citation chips like [1] to inspect the exact source text and faithfulness score.",
          done: false,
        },
      ]
    : [
        {
          icon: <FileText size={22} />,
          num: "1",
          title: "Select Two Documents",
          desc: "Check exactly 2 documents in the sidebar to enable comparison mode.",
          done: false,
        },
        {
          icon: <MessageSquare size={22} />,
          num: "2",
          title: "Ask a Comparison Question",
          desc: 'E.g., "What are the key differences between these two reports?"',
          done: false,
        },
        {
          icon: <Zap size={22} />,
          num: "3",
          title: "Review Side-by-Side",
          desc: "The AI pulls relevant passages from both documents and highlights differences.",
          done: false,
        },
      ];

  return (
    <div className="onboarding-empty">
      <div className="onboarding-hero">
        <div className="onboarding-icon">
          <Sparkles size={32} />
        </div>
        <h2>
          {mode === "chat"
            ? `Welcome, ${user?.name || "there"}!`
            : "Compare Mode"}
        </h2>
        <p>
          {mode === "chat"
            ? "Your AI-powered research assistant. Upload documents, ask questions, and get answers backed by verifiable citations."
            : "Analyze and contrast two documents. Upload your PDFs, select two, then ask a question to get a side-by-side comparison."}
        </p>
      </div>

      <div className="onboarding-steps">
        <h3>How it works</h3>
        <div className="steps-grid">
          {steps.map((s, i) => (
            <div key={i} className={`step-card ${s.done ? "done" : ""}`} style={{ animationDelay: `${i * 0.1}s` }}>
              <div className="step-num">{s.num}</div>
              <div className="step-icon">{s.icon}</div>
              <h4>{s.title}</h4>
              <p>{s.desc}</p>
              {s.done && (
                <div className="step-done-badge">
                  <CheckCircle2 size={12} /> Done
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   FAITHFULNESS BADGE
   ================================================================ */
function FaithfulnessBadge({ score }) {
  const level = faithLevel(score);
  const pct = Math.round(score * 100);
  const Icon =
    level === "high"
      ? ShieldCheck
      : level === "medium"
      ? ShieldAlert
      : ShieldX;

  return (
    <div className={`faithfulness-badge ${level}`}>
      <Icon size={14} />
      Faithfulness: {pct}%
    </div>
  );
}

/* ================================================================
   SOURCE DETAIL PANEL
   ================================================================ */
function SourceDetail({ cite, faithfulness, allCitations, onSelect }) {
  const verdicts = faithfulness?.citation_verdicts || [];
  const numOnly =
    typeof cite.n === "string"
      ? parseInt(cite.n.replace(/[AB]/, ""), 10)
      : cite.n;
  const verdict = findVerdict(verdicts, numOnly);

  return (
    <div className="cite-detail">
      {/* Header */}
      <div className="cite-header">
        <span className="cite-num">{cite.n}</span>
        <div>
          <div className="cite-doc">{cite.doc_name}</div>
          <div className="cite-page">Page {cite.page + 1}</div>
        </div>
      </div>

      {/* Score */}
      <div className="cite-score">
        <ChevronRight size={12} />
        Similarity: {cite.score?.toFixed(3) || "N/A"}
      </div>

      {/* Verification status */}
      {verdict ? (
        <div
          className={`verification-status ${
            verdict.supported ? "supported" : "unsupported"
          }`}
        >
          {verdict.supported ? (
            <>
              <CheckCircle2 size={14} /> Verified — source supports this claim
            </>
          ) : (
            <>
              <XCircle size={14} /> Unverified — claim not fully supported
            </>
          )}
        </div>
      ) : (
        <div className="verification-status unknown">
          <Info size={14} /> No verification data for this citation
        </div>
      )}

      {verdict?.explanation && (
        <p
          style={{
            fontSize: 12,
            color: "var(--text-secondary)",
            marginBottom: 12,
            lineHeight: 1.6,
          }}
        >
          {verdict.explanation}
        </p>
      )}

      {/* Source text */}
      <div className="cite-text-label">
        <FileText size={12} />
        Source Text
      </div>
      <div className="cite-text">{cite.text}</div>

      {/* All retrieved */}
      {allCitations.length > 1 && (
        <div className="retrieved-list">
          <h3>All Retrieved Sources</h3>
          <ul>
            {allCitations.map((c) => (
              <li key={c.n}>
                <button
                  className={`src-link ${
                    String(c.n) === String(cite.n) ? "active" : ""
                  }`}
                  onClick={() => onSelect(c)}
                >
                  <span className="src-num">{c.n}</span>
                  {c.doc_name} · p{c.page + 1}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Faithfulness detail */}
      {faithfulness && faithfulness.faithfulness_score >= 0 && (
        <div className="faith-detail">
          <h3>Faithfulness Analysis</h3>
          <div className="faith-score-bar">
            <div
              className={`faith-score-fill ${faithLevel(
                faithfulness.faithfulness_score
              )}`}
              style={{
                width: `${Math.round(
                  faithfulness.faithfulness_score * 100
                )}%`,
              }}
            />
          </div>
          <p className="faith-reasoning">
            {faithfulness.reasoning || "No reasoning provided."}
          </p>
        </div>
      )}
    </div>
  );
}

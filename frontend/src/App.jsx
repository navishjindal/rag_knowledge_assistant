import { useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function renderAnswer(text, onCite) {
  // Split on [n] citation markers and turn them into clickable chips
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((p, i) => {
    const m = p.match(/^\[(\d+)\]$/);
    if (m) {
      const n = parseInt(m[1], 10);
      return (
        <button key={i} className="cite" onClick={() => onCite(n)}>
          {p}
        </button>
      );
    }
    return <span key={i}>{p}</span>;
  });
}

export default function App() {
  const [docs, setDocs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeCite, setActiveCite] = useState(null);
  const [uploadMsg, setUploadMsg] = useState("");
  const fileRef = useRef(null);
  const bottomRef = useRef(null);

  const refreshDocs = async () => {
    try {
      const r = await fetch(`${API}/documents`);
      setDocs(await r.json());
    } catch {
      /* backend not up yet */
    }
  };

  useEffect(() => {
    refreshDocs();
  }, []);

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
      const r = await fetch(`${API}/documents`, { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "upload failed");
      setUploadMsg(`✓ ${data.name}: ${data.chunks} chunks indexed`);
      refreshDocs();
    } catch (err) {
      setUploadMsg(`✗ ${err.message}`);
    }
    fileRef.current.value = "";
  };

  const ask = async (e) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;
    setQuestion("");
    setActiveCite(null);
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const r = await fetch(`${API}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, top_k: 5, rerank: true }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "query failed");
      setMessages((m) => [
        ...m,
        { role: "assistant", text: data.answer, citations: data.citations },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Error: ${err.message}`, citations: [] },
      ]);
    }
    setLoading(false);
  };

  const lastCitations =
    [...messages].reverse().find((m) => m.citations?.length)?.citations || [];

  return (
    <div className="layout">
      <aside className="sidebar">
        <h2>Documents</h2>
        <label className="upload-btn">
          + Upload PDF
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            hidden
            onChange={upload}
          />
        </label>
        {uploadMsg && <p className="upload-msg">{uploadMsg}</p>}
        <ul>
          {docs.map((d) => (
            <li key={d.doc_id}>
              <span className="doc-name">{d.name}</span>
              <span className="doc-meta">{d.chunks} chunks</span>
            </li>
          ))}
        </ul>
        {docs.length === 0 && (
          <p className="hint">No documents yet — upload a PDF to start.</p>
        )}
      </aside>

      <main className="chat">
        <div className="messages">
          {messages.length === 0 && (
            <p className="hint center">
              Upload a PDF on the left, then ask a question.
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <div className="bubble">
                {m.role === "assistant"
                  ? renderAnswer(m.text, (n) => {
                      const c = (m.citations || []).find((x) => x.n === n);
                      if (c) setActiveCite(c);
                    })
                  : m.text}
              </div>
            </div>
          ))}
          {loading && (
            <div className="msg assistant">
              <div className="bubble thinking">Retrieving & generating…</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <form className="composer" onSubmit={ask}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about your documents…"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !question.trim()}>
            Ask
          </button>
        </form>
      </main>

      <aside className={`sources ${activeCite ? "open" : ""}`}>
        <h2>Source</h2>
        {activeCite ? (
          <>
            <p className="src-meta">
              [{activeCite.n}] {activeCite.doc_name} · page{" "}
              {activeCite.page + 1} · score {activeCite.score.toFixed(3)}
            </p>
            <p className="src-text">{activeCite.text}</p>
            {lastCitations.length > 1 && (
              <>
                <h3>All retrieved</h3>
                <ul>
                  {lastCitations.map((c) => (
                    <li key={c.n}>
                      <button
                        className="src-link"
                        onClick={() => setActiveCite(c)}
                      >
                        [{c.n}] {c.doc_name} · p{c.page + 1}
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </>
        ) : (
          <p className="hint">Click a [n] citation to inspect its source.</p>
        )}
      </aside>
    </div>
  );
}

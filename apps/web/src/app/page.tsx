"use client";

import {
    Check,
    ChevronDown,
    CircleAlert,
    Database,
    FileText,
    LoaderCircle,
    RefreshCw,
    Search,
    Send,
    Settings2,
    Sparkles,
    Trash2,
    Workflow,
    X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
    askQuestion,
    forgetDocuments,
    getDocuments,
    getHealth,
    ingestDocuments,
    type AskResponse,
    type KnowledgeDocument,
    type ServiceHealth,
} from "@/lib/api";

type ChatTurn = {
    question: string;
    result?: AskResponse;
    error?: string;
    loading?: boolean;
};

const suggestions = [
    "What should staff do when a delivery attempt is disputed?",
    "Which evidence is needed to investigate a damaged parcel?",
    "How should an overdue shipment exception be escalated?",
];

const serviceLabels: Record<string, string> = {
    postgres: "PostgreSQL",
    qdrant: "Qdrant",
    ollama: "Ollama",
};

export default function Home() {
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [health, setHealth] = useState<ServiceHealth | null>(null);
    const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
    const [documentTotal, setDocumentTotal] = useState(0);
    const [databaseRecords, setDatabaseRecords] = useState(0);
    const [question, setQuestion] = useState("");
    const [turns, setTurns] = useState<ChatTurn[]>([]);
    const [isIngesting, setIsIngesting] = useState(false);
    const [isForgetting, setIsForgetting] = useState(false);
    const [notice, setNotice] = useState("");
    const [isAsking, setIsAsking] = useState(false);

    const refreshSettings = useCallback(async () => {
        const [healthResult, docsResult] = await Promise.allSettled([getHealth(), getDocuments()]);
        if (healthResult.status === "fulfilled") setHealth(healthResult.value);
        if (docsResult.status === "fulfilled") {
            setDocuments(docsResult.value.documents);
            setDocumentTotal(docsResult.value.total);
            setDatabaseRecords(docsResult.value.database_records);
        }
    }, []);

    useEffect(() => {
        void refreshSettings();
        const timer = window.setInterval(() => void refreshSettings(), 20000);
        return () => window.clearInterval(timer);
    }, [refreshSettings]);

    useEffect(() => {
        if (!settingsOpen) return;
        function onKeyDown(event: KeyboardEvent) {
            if (event.key === "Escape") setSettingsOpen(false);
        }
        window.addEventListener("keydown", onKeyDown);
        return () => window.removeEventListener("keydown", onKeyDown);
    }, [settingsOpen]);

    async function handleIngest() {
        setIsIngesting(true);
        setNotice("");
        try {
            const result = await ingestDocuments();
            setNotice(`Indexed ${result.documents} documents, ${result.chunks} passages, and ${result.database_records} PostgreSQL records.`);
            await refreshSettings();
        } catch (error) {
            setNotice(error instanceof Error ? error.message : "Indexing failed.");
        } finally {
            setIsIngesting(false);
        }
    }

    async function handleForget() {
        const indexedCount = documentTotal + databaseRecords;
        if (!window.confirm(`Forget the indexed documents and ${databaseRecords} PostgreSQL records? Original source files and PostgreSQL tables will not be deleted.`)) return;
        setIsForgetting(true);
        setNotice("");
        try {
            const result = await forgetDocuments();
            setNotice(`Forgot ${result.items_forgotten || indexedCount} indexed items. Source files and PostgreSQL tables are unchanged.`);
            await refreshSettings();
        } catch (error) {
            setNotice(error instanceof Error ? error.message : "Could not forget the index.");
        } finally {
            setIsForgetting(false);
        }
    }

    async function handleAsk(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const submittedQuestion = question.trim();
        if (!submittedQuestion || isAsking) return;
        setQuestion("");
        setIsAsking(true);
        const turnIndex = turns.length;
        setTurns((current) => [...current, { question: submittedQuestion, loading: true }]);
        try {
            const result = await askQuestion(submittedQuestion);
            setTurns((current) => current.map((turn, index) => index === turnIndex ? { question: submittedQuestion, result } : turn));
        } catch (error) {
            setTurns((current) => current.map((turn, index) => index === turnIndex ? { question: submittedQuestion, error: error instanceof Error ? error.message : "Request failed." } : turn));
        } finally {
            setIsAsking(false);
        }
    }

    const connectedServices = health ? Object.values(health.services).filter((status) => status === "ok").length : 0;

    return (
        <main className="chatgpt-shell">
            <header className="chatgpt-topbar">
                <a className="brand" href="#workspace" aria-label="Ditiro home">
                    <span className="brand-mark"><Workflow size={18} /></span>
                    <span className="brand-word">ditiro<span>.</span></span>
                </a>
                <span className="local-status"><i /> Local</span>
            </header>

            {notice && <div className="notice chat-notice" role="status"><Check size={15} />{notice}<button onClick={() => setNotice("")} aria-label="Dismiss notification">×</button></div>}

            <section className="chatgpt-conversation" id="workspace" aria-live="polite">
                {turns.length === 0 ? <div className="chatgpt-welcome">
                    <span className="chatgpt-spark"><Sparkles size={21} /></span>
                    <h1>What can I help you find?</h1>
                    <p>Answers are based on indexed documents and PostgreSQL records.</p>
                    <div className="chatgpt-suggestions">{suggestions.map((suggestion) => <button key={suggestion} onClick={() => setQuestion(suggestion)}>{suggestion}<ChevronDown size={14} /></button>)}</div>
                </div> : <div className="chatgpt-turns">{turns.map((turn, index) => <article className="chatgpt-turn" key={`${turn.question}-${index}`}>
                    <div className="chatgpt-user"><span>You</span><p>{turn.question}</p></div>
                    <div className="chatgpt-answer"><span className="assistant-mark"><Sparkles size={15} /></span>
                        {turn.loading ? <div className="thinking"><LoaderCircle size={16} className="spin" />Searching indexed evidence…</div> : turn.error ? <div className="answer-error"><CircleAlert size={16} />{turn.error}</div> : <>
                            <div className="answer-text">{turn.result?.answer}</div>
                            {turn.result?.sources.length ? <div className="chatgpt-sources">{turn.result.sources.map((source) => <details className="evidence-item" key={`${source.ref}-${source.chunk_index}`}><summary><span className="source-ref">{source.ref}</span><span className="evidence-title">{source.title.replaceAll("_", " ")}<small>{source.source_type} · {source.source_uri} · passage {source.chunk_index + 1}</small></span><span className="relevance">{Math.round(source.score * 100)}%<small>similarity</small></span><ChevronDown size={14} /></summary><p>{source.text}</p></details>)}</div> : <div className="no-evidence"><CircleAlert size={15} />No matching indexed evidence was found.</div>}
                        </>}
                    </div>
                </article>)}</div>}
            </section>

            <div className="chatgpt-bottom">
                <form className="chatgpt-composer" onSubmit={(event) => void handleAsk(event)}>
                    <textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Ask about your indexed logistics knowledge" rows={2} maxLength={2000} aria-label="Ask a question" />
                    <div className="composer-controls"><span>Answers use retrieved sources only</span><button type="submit" disabled={!question.trim() || isAsking} aria-label="Send question">{isAsking ? <LoaderCircle size={16} className="spin" /> : <Send size={16} />}</button></div>
                </form>
                <p className="chatgpt-disclaimer">Check cited sources before making operational decisions.</p>
                <button className="settings-launcher" onClick={() => { setSettingsOpen(true); void refreshSettings(); }}><Settings2 size={16} />Settings</button>
            </div>

            {settingsOpen && <div className="settings-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSettingsOpen(false); }}>
                <section className="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title">
                    <header className="settings-modal-head"><div><span className="section-kicker">DITIRO WORKSPACE</span><h2 id="settings-title">Settings</h2></div><button className="icon-button" onClick={() => setSettingsOpen(false)} aria-label="Close settings"><X size={17} /></button></header>
                    <div className="settings-modal-content">
                        <section className="settings-section">
                            <div className="settings-section-head"><div><span className="section-kicker">LOCAL SERVICES</span><h3>System status</h3></div><span className={`health-pill ${health?.status === "ok" ? "healthy" : "degraded"}`}><i />{health?.status === "ok" ? "Ready" : health ? "Degraded" : "Checking"}</span></div>
                            <div className="health-grid">{Object.entries(serviceLabels).map(([key, label]) => { const status = health?.services[key]; return <div className="health-card" key={key}><span className={`service-dot ${status === "ok" ? "ok" : status ? "down" : "pending"}`} /><div><strong>{label}</strong><span>{status || "checking"}</span></div></div>; })}</div>
                            <div className="settings-models"><span>Generation <b>{health?.model || "llama3.2:1b"}</b></span><span>Embeddings <b>{health?.embedding_model || "all-MiniLM-L6-v2"}</b></span><span>Qdrant collection <b>{health?.collection || "ditiro_logistics"}</b></span></div>
                        </section>
                        <section className="settings-section">
                            <div className="settings-section-head"><div><span className="section-kicker">INDEXED KNOWLEDGE</span><h3>Sources</h3></div><button className="icon-button" onClick={() => void refreshSettings()} aria-label="Refresh indexed data"><RefreshCw size={15} /></button></div>
                            <div className="index-counts"><div><FileText size={16} /><span><b>{documentTotal}</b> documents</span></div><div><Database size={16} /><span><b>{databaseRecords}</b> PostgreSQL records</span></div></div>
                            {documents.length ? <div className="settings-docs">{documents.map((document) => <div className="settings-doc-row" key={document.document_id}><FileText size={14} /><strong>{document.title.replaceAll("_", " ")}</strong><span>{document.document_type.toUpperCase()}</span></div>)}{documentTotal > documents.length && <div className="doc-more">Showing {documents.length} of {documentTotal} documents.</div>}</div> : <div className="settings-empty">No documents indexed yet.</div>}
                            <p className="settings-note">Re-indexing reads files under <code>docs/</code> and supported PostgreSQL logistics tables. Forgetting removes indexed vectors and document metadata, not original files or database rows.</p>
                            <div className="settings-actions"><button className="secondary-button" onClick={() => void handleIngest()} disabled={isIngesting}><Database size={15} />{isIngesting ? "Indexing…" : "Re-index sources"}</button><button className="danger-button" onClick={() => void handleForget()} disabled={isForgetting || (documentTotal === 0 && databaseRecords === 0)}><Trash2 size={15} />{isForgetting ? "Forgetting…" : "Forget index"}</button></div>
                        </section>
                    </div>
                    <footer className="settings-modal-foot"><span>{connectedServices}/3 services connected</span><button onClick={() => setSettingsOpen(false)}>Done</button></footer>
                </section>
            </div>}
        </main>
    );
}

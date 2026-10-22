export type ServiceHealth = {
    status: "ok" | "degraded";
    services: Record<string, string>;
    model: string;
    embedding_model: string;
    collection: string;
};

export type KnowledgeDocument = {
    document_id: string;
    title: string;
    document_type: string;
    source_uri: string | null;
    content_sha256: string;
    indexed_at: string;
};

export type EvidenceSource = {
    ref: string;
    title: string;
    source_uri: string;
    chunk_index: number;
    text: string;
    score: number;
    source_type: "document" | "database";
};

export type AskResponse = {
    answer: string;
    sources: EvidenceSource[];
};

const apiUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${apiUrl}${path}`, {
        ...init,
        headers: { "Content-Type": "application/json", ...init?.headers },
        cache: "no-store",
    });
    if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail || `Request failed (${response.status})`);
    }
    return response.json() as Promise<T>;
}

export const getHealth = () => request<ServiceHealth>("/health");
export const getDocuments = () =>
    request<{ documents: KnowledgeDocument[]; total: number; database_records: number }>("/documents");
export const ingestDocuments = () =>
    request<{ documents: number; chunks: number; database_records: number }>("/ingest", { method: "POST" });
export const forgetDocuments = () =>
    request<{ items_forgotten: number }>("/documents", { method: "DELETE" });
export const askQuestion = (question: string) =>
    request<AskResponse>("/ask", {
        method: "POST",
        body: JSON.stringify({ question, limit: 5 }),
    });
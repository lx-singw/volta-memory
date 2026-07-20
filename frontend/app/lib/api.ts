"use client";

/**
 * Browser-facing contracts for the tenant-scoped Volta API.  The server owns
 * identity through its session cookie; this client never sends an entity id.
 */
export type MemoryStatus = "eligible" | "needs_reconfirmation" | "retained" | "excluded";
export type MemoryType = "fact" | "preference" | "correction" | "outcome" | "consolidated" | "evidence";

export type MemoryReference = {
  id: string;
  observation: string;
  sourceQuote: string | null;
  sourceTurnIndex: number | null;
};

export type MemoryProvenance = {
  sourceQuote: string | null;
  sourceTurnIndex: number | null;
  sourceVerified: boolean;
  isConstraint: boolean | null;
  prior: MemoryReference | null;
};

export type MemoryRelation = {
  id?: string;
  sourceMemoryId: string;
  targetMemoryId: string;
  relationType: "supersedes" | "reinforces" | "consolidates";
  createdAt?: string | null;
};

export type MemoryDTO = {
  id: string;
  observation: string;
  memoryType: MemoryType;
  profileSlot: string;
  confidence: number;
  importance: number | null;
  status: MemoryStatus;
  lastConfirmedAt: string | null;
  createdAt?: string | null;
  supersededById?: string | null;
  provenance: MemoryProvenance;
  relationships?: MemoryRelation[];
  exclusionReason?: string | null;
};

export type ProfileFact = {
  profileSlot: string;
  label?: string | null;
  displayValue: string;
  status: MemoryStatus;
  confidence: number | null;
  lastConfirmedAt: string | null;
  /** The durable record backing this display fact. Never infer it in the UI. */
  sourceMemoryId: string | null;
  sourceTurnIndex?: number | null;
  sourceVerified?: boolean;
};

export type ProfileDTO = {
  facts: ProfileFact[];
  currentFactCount: number;
  retainedFactCount: number;
  lastConfirmedAt: string | null;
};

export type ExcludedMemoryTrace = {
  memoryId: string;
  reason: string | null;
  observation: string | null;
  sourceQuote: string | null;
  sourceTurnIndex: number | null;
  sourceVerified: boolean;
};

export type ExplainTrace = {
  referencedMemoryIds: string[];
  primaryInfluenceMemoryId: string | null;
  confidenceTierChoice: string | null;
  counterfactual: string | null;
  usedMemoryIds: string[];
  availableMemoryIds: string[];
  /**
   * These entries are emitted by the retrieval/trace layer.  They are not
   * inferred from a memory's current status in the browser, because a retained
   * record is not necessarily relevant to every answer.
   */
  excludedMemories: ExcludedMemoryTrace[];
};

export type MessageDTO = {
  id?: string;
  role: "user" | "assistant";
  content: string;
  createdAt?: string | null;
  memoryContext?: MemoryDTO[];
  explainTrace?: ExplainTrace | null;
};

export type LifecycleChange = {
  action: "created" | "reinforced" | "corrected" | "excluded" | "reconfirmed" | "none";
  before: MemoryReference | null;
  after: MemoryReference | null;
  sourceQuote?: string | null;
  sourceTurnIndex?: number | null;
  sourceVerified?: boolean;
};

export type EndSessionResult = {
  sessionId: string;
  memoryChanges: LifecycleChange[];
};

export type RuntimeConfig = {
  apiBaseUrl?: string;
  csrfHeaderName?: string;
  csrfCookieName?: string;
  legacyEntityId?: string;
};

export type WorkspaceDTO = {
  entityId: string;
  entityType: "showcase" | "anonymous" | "user";
  csrfToken: string | null;
};

declare global {
  interface Window {
    __VOLTA_RUNTIME_CONFIG__?: Record<string, unknown>;
  }
}

// A build may be exported once and served in several environments.  The
// injected runtime file is therefore authoritative.  A build-time URL is only
// a local-development convenience and is deliberately never a production
// localhost fallback.
const buildTimeBaseUrl = (process.env.NODE_ENV !== "production" ? process.env.NEXT_PUBLIC_API_BASE_URL || "" : "").replace(/\/$/, "");
let runtimeConfigPromise: Promise<RuntimeConfig> | null = null;

function camel(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}

function str(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function num(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function bool(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function memoryStatus(value: unknown, isSuperseded = false): MemoryStatus {
  if (value === "eligible" || value === "needs_reconfirmation" || value === "retained" || value === "excluded") return value;
  return isSuperseded ? "retained" : "eligible";
}

function memoryType(value: unknown): MemoryType {
  return value === "fact" || value === "preference" || value === "correction" || value === "outcome" || value === "consolidated" || value === "evidence" ? value : "evidence";
}

function normalizeReference(value: unknown): MemoryReference | null {
  const source = camel(value);
  const id = str(source.id) || str(source.memory_id);
  const observation = str(source.observation) || str(source.content) || str(source.text);
  if (!id || !observation) return null;
  return {
    id,
    observation,
    sourceQuote: str(source.sourceQuote) || str(source.source_quote),
    sourceTurnIndex: typeof source.sourceTurnIndex === "number" ? source.sourceTurnIndex : typeof source.source_turn_index === "number" ? source.source_turn_index : null,
  };
}

export function normalizeMemory(value: unknown): MemoryDTO {
  const source = camel(value);
  const evidence = camel(source.evidence);
  const provenanceRaw = camel(source.provenance);
  const isSuperseded = bool(source.isSuperseded, bool(source.is_superseded));
  const rawProvenance = Object.keys(provenanceRaw).length ? provenanceRaw : evidence;
  const prior = normalizeReference(rawProvenance.prior) || normalizeReference(rawProvenance.supersedes);
  const id = str(source.id) || str(source.memoryId) || str(source.memory_id) || crypto.randomUUID();
  const observation = str(source.observation) || str(source.content) || str(source.text) || "Untitled memory";
  const relations = Array.isArray(source.relationships) ? source.relationships.map(normalizeRelation).filter(Boolean) as MemoryRelation[] : undefined;
  return {
    id,
    observation,
    memoryType: memoryType(source.memoryType || source.memory_type),
    profileSlot: str(source.profileSlot) || str(source.profile_slot) || "none",
    confidence: num(source.confidence ?? source.effective_confidence ?? source.base_confidence, 0.5),
    importance: typeof source.importance === "number" ? source.importance : typeof source.importanceScore === "number" ? source.importanceScore : typeof source.importance_score === "number" ? source.importance_score : null,
    status: memoryStatus(source.status, isSuperseded),
    lastConfirmedAt: str(source.lastConfirmedAt) || str(source.last_reinforced_at) || str(source.last_confirmed_at),
    createdAt: str(source.createdAt) || str(source.created_at),
    supersededById: str(source.supersededById) || str(source.superseded_by_id),
    provenance: {
      sourceQuote: str(rawProvenance.sourceQuote) || str(rawProvenance.source_quote),
      sourceTurnIndex: typeof rawProvenance.sourceTurnIndex === "number" ? rawProvenance.sourceTurnIndex : typeof rawProvenance.source_turn_index === "number" ? rawProvenance.source_turn_index : null,
      sourceVerified: bool(rawProvenance.sourceVerified, bool(rawProvenance.source_verified)),
      isConstraint: typeof rawProvenance.isConstraint === "boolean" ? rawProvenance.isConstraint : typeof rawProvenance.is_constraint === "boolean" ? rawProvenance.is_constraint : null,
      prior,
    },
    relationships: relations,
    exclusionReason: str(source.exclusionReason) || str(source.exclusion_reason),
  };
}

function normalizeRelation(value: unknown): MemoryRelation | null {
  const source = camel(value);
  const sourceMemoryId = str(source.sourceMemoryId) || str(source.source_memory_id);
  const targetMemoryId = str(source.targetMemoryId) || str(source.target_memory_id);
  const relationType = source.relationType || source.relation_type;
  if (!sourceMemoryId || !targetMemoryId || (relationType !== "supersedes" && relationType !== "reinforces" && relationType !== "consolidates")) return null;
  return { id: str(source.id) || undefined, sourceMemoryId, targetMemoryId, relationType, createdAt: str(source.createdAt) || str(source.created_at) };
}

function normalizeProfile(value: unknown): ProfileDTO {
  const source = camel(value);
  const rawFacts = Array.isArray(source.facts) ? source.facts : Array.isArray(source.profile) ? source.profile : [];
  const facts = rawFacts.map((fact): ProfileFact => {
    const entry = camel(fact);
    const isSuperseded = bool(entry.isSuperseded, bool(entry.is_superseded));
    return {
      profileSlot: str(entry.profileSlot) || str(entry.profile_slot) || str(entry.slot) || "none",
      label: str(entry.label),
      displayValue: str(entry.displayValue) || str(entry.display_value) || str(entry.value) || str(entry.observation) || "Unknown",
      status: memoryStatus(entry.status, isSuperseded),
      confidence: typeof entry.confidence === "number" ? entry.confidence : null,
      lastConfirmedAt: str(entry.lastConfirmedAt) || str(entry.last_confirmed_at) || str(entry.last_reinforced_at),
      sourceMemoryId: str(entry.sourceMemoryId) || str(entry.source_memory_id) || str(entry.memoryId) || str(entry.memory_id) || str(entry.id),
      sourceTurnIndex: typeof entry.sourceTurnIndex === "number" ? entry.sourceTurnIndex : typeof entry.source_turn_index === "number" ? entry.source_turn_index : null,
      sourceVerified: bool(entry.sourceVerified, bool(entry.source_verified)),
    };
  });
  return {
    facts,
    currentFactCount: num(source.currentFactCount ?? source.current_fact_count ?? source.eligibleCount ?? source.eligible_count, facts.filter((fact) => fact.status === "eligible").length),
    retainedFactCount: num(source.retainedFactCount ?? source.retained_fact_count ?? source.retainedCount ?? source.retained_count, facts.filter((fact) => fact.status === "retained").length),
    lastConfirmedAt: str(source.lastConfirmedAt) || str(source.last_confirmed_at),
  };
}

function normalizeTrace(value: unknown): ExplainTrace | null {
  if (!value) return null;
  const source = camel(value);
  const ids = (input: unknown) => Array.isArray(input) ? input.filter((id): id is string => typeof id === "string") : [];
  const rawExcluded = Array.isArray(source.excludedMemories) ? source.excludedMemories : Array.isArray(source.excluded_memories) ? source.excluded_memories : [];
  return {
    referencedMemoryIds: ids(source.referencedMemoryIds || source.referenced_memory_ids),
    primaryInfluenceMemoryId: str(source.primaryInfluenceMemoryId) || str(source.primary_influence_memory_id),
    confidenceTierChoice: str(source.confidenceTierChoice) || str(source.confidence_tier_choice),
    counterfactual: str(source.counterfactual),
    usedMemoryIds: ids(source.usedMemoryIds || source.used_memory_ids || source.referencedMemoryIds || source.referenced_memory_ids),
    availableMemoryIds: ids(source.availableMemoryIds || source.available_memory_ids),
    excludedMemories: rawExcluded.map((item) => {
      const excluded = camel(item);
      const snapshot = [excluded.memory, excluded.snapshot, excluded.memory_snapshot]
        .map(camel)
        .find((candidate) => Object.keys(candidate).length > 0) || {};
      const snapshotProvenance = camel(snapshot.provenance);
      const sourceQuote = str(excluded.sourceQuote) || str(excluded.source_quote) || str(snapshotProvenance.sourceQuote) || str(snapshotProvenance.source_quote);
      const sourceTurnIndex = typeof excluded.sourceTurnIndex === "number" ? excluded.sourceTurnIndex
        : typeof excluded.source_turn_index === "number" ? excluded.source_turn_index
          : typeof snapshotProvenance.sourceTurnIndex === "number" ? snapshotProvenance.sourceTurnIndex
            : typeof snapshotProvenance.source_turn_index === "number" ? snapshotProvenance.source_turn_index : null;
      const sourceVerified = bool(excluded.sourceVerified, bool(excluded.source_verified,
        bool(snapshotProvenance.sourceVerified, bool(snapshotProvenance.source_verified))));
      return {
        memoryId: str(excluded.memoryId) || str(excluded.memory_id) || str(snapshot.id) || "",
        reason: str(excluded.reason),
        observation: str(excluded.observation) || str(snapshot.observation) || null,
        sourceQuote,
        sourceTurnIndex,
        sourceVerified,
      };
    }).filter((item) => item.memoryId),
  };
}

function snapshotProvenance(value: unknown) {
  const snapshot = camel(value);
  const provenance = camel(snapshot.provenance);
  const evidence = camel(snapshot.evidence);
  const source = Object.keys(provenance).length ? provenance : evidence;
  return {
    sourceQuote: str(source.sourceQuote) || str(source.source_quote),
    sourceTurnIndex: typeof source.sourceTurnIndex === "number" ? source.sourceTurnIndex : typeof source.source_turn_index === "number" ? source.source_turn_index : null,
    sourceVerified: bool(source.sourceVerified, bool(source.source_verified)),
  };
}

function normalizeChange(value: unknown): LifecycleChange {
  const source = camel(value);
  const rawAction = source.action || source.operation;
  const action = rawAction === "created" || rawAction === "reinforced" || rawAction === "corrected" || rawAction === "excluded" || rawAction === "reconfirmed" ? rawAction : "none";
  const afterProvenance = snapshotProvenance(source.after);
  const beforeProvenance = snapshotProvenance(source.before);
  const sourceQuote = str(source.sourceQuote) || str(source.source_quote) || afterProvenance.sourceQuote || beforeProvenance.sourceQuote;
  const sourceTurnIndex = typeof source.sourceTurnIndex === "number" ? source.sourceTurnIndex
    : typeof source.source_turn_index === "number" ? source.source_turn_index
      : afterProvenance.sourceTurnIndex ?? beforeProvenance.sourceTurnIndex;
  const sourceVerified = typeof source.sourceVerified === "boolean" ? source.sourceVerified
    : typeof source.source_verified === "boolean" ? source.source_verified
      : afterProvenance.sourceVerified || beforeProvenance.sourceVerified;
  return {
    action,
    before: normalizeReference(source.before),
    after: normalizeReference(source.after),
    sourceQuote,
    sourceTurnIndex,
    sourceVerified,
  };
}

function normalizeWorkspace(value: unknown): WorkspaceDTO {
  const source = camel(value);
  const entityType = str(source.entityType) || str(source.entity_type);
  return {
    entityId: str(source.entityId) || str(source.entity_id) || "",
    entityType: entityType === "showcase" || entityType === "user" ? entityType : "anonymous",
    csrfToken: str(source.csrfToken) || str(source.csrf_token),
  };
}

function cookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${encodeURIComponent(name)}=`;
  return document.cookie.split("; ").find((entry) => entry.startsWith(prefix))?.slice(prefix.length) || null;
}

export async function getRuntimeConfig(): Promise<RuntimeConfig> {
  if (!runtimeConfigPromise) {
    const injected = typeof window !== "undefined" ? camel(window.__VOLTA_RUNTIME_CONFIG__) : {};
    runtimeConfigPromise = (Object.keys(injected).length ? Promise.resolve(injected) : fetch("/runtime-config.json", { cache: "no-store" })
      .then(async (response) => response.ok ? camel(await response.json()) : {}))
      .then((config): RuntimeConfig => ({
        apiBaseUrl: (str(config.apiBaseUrl) || str(config.api_base_url) || buildTimeBaseUrl).replace(/\/$/, ""),
        csrfHeaderName: str(config.csrfHeaderName) || str(config.csrf_header_name) || "X-CSRF-Token",
        csrfCookieName: str(config.csrfCookieName) || str(config.csrf_cookie_name) || "volta_csrf",
        legacyEntityId: str(config.legacyEntityId) || str(config.legacy_entity_id) || undefined,
      }))
      .catch(() => ({ apiBaseUrl: buildTimeBaseUrl, csrfHeaderName: "X-CSRF-Token", csrfCookieName: "volta_csrf" }));
  }
  return runtimeConfigPromise;
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly body?: unknown) {
    super(message);
  }
}

export class VoltaApi {
  private csrfToken: string | null = null;

  constructor(private readonly config: RuntimeConfig) {}

  private url(path: string): string {
    return `${(this.config.apiBaseUrl || "").replace(/\/$/, "")}${path}`;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    if (init.method && !["GET", "HEAD", "OPTIONS"].includes(init.method.toUpperCase())) {
      const token = this.csrfToken || cookie(this.config.csrfCookieName || "volta_csrf");
      if (token) headers.set(this.config.csrfHeaderName || "X-CSRF-Token", decodeURIComponent(token));
    }
    const response = await fetch(this.url(path), { ...init, headers, credentials: "include" });
    const body = response.status === 204 ? null : await response.json().catch(async () => await response.text());
    if (!response.ok) {
      const detail = camel(body).detail;
      throw new ApiError(typeof detail === "string" ? detail : `Request failed (${response.status})`, response.status, body);
    }
    return body as T;
  }

  async getProfile(): Promise<ProfileDTO> {
    return normalizeProfile(await this.request<unknown>("/v1/me/profile"));
  }

  /** Bootstrap the opaque cookie session and cache the matching CSRF token. */
  async getWorkspace(): Promise<WorkspaceDTO> {
    const workspace = normalizeWorkspace(await this.request<unknown>("/v1/me"));
    this.csrfToken = workspace.csrfToken;
    return workspace;
  }

  async requestMagicLink(email: string): Promise<void> {
    await this.request<unknown>("/v1/auth/request-link", { method: "POST", body: JSON.stringify({ email }) });
  }

  async verifyMagicLink(token: string): Promise<WorkspaceDTO> {
    const workspace = normalizeWorkspace(await this.request<unknown>("/v1/auth/verify", { method: "POST", body: JSON.stringify({ token }) }));
    this.csrfToken = workspace.csrfToken;
    return workspace;
  }

  async exportWorkspace(): Promise<unknown> {
    return this.request<unknown>("/v1/me/export");
  }

  async deleteWorkspace(): Promise<void> {
    await this.request<unknown>("/v1/me", { method: "DELETE" });
    this.csrfToken = null;
  }

  async getMemories(): Promise<{ memories: MemoryDTO[]; relationships: MemoryRelation[] }> {
    const response = camel(await this.request<unknown>("/v1/me/memories"));
    const memories = (Array.isArray(response.memories) ? response.memories : []).map(normalizeMemory);
    const relationships = (Array.isArray(response.relationships) ? response.relationships : []).map(normalizeRelation).filter(Boolean) as MemoryRelation[];
    return { memories, relationships };
  }

  async getTimeline(): Promise<MemoryDTO[]> {
    const response = camel(await this.request<unknown>("/v1/me/memory-timeline"));
    const entries = Array.isArray(response.timeline) ? response.timeline : Array.isArray(response.memories) ? response.memories : [];
    return entries.map(normalizeMemory);
  }

  async getShowcaseMemories(): Promise<{ memories: MemoryDTO[]; relationships: MemoryRelation[] }> {
    const response = camel(await this.request<unknown>("/v1/showcase/memories"));
    const memories = (Array.isArray(response.memories) ? response.memories : []).map(normalizeMemory);
    const relationships = (Array.isArray(response.relationships) ? response.relationships : []).map(normalizeRelation).filter(Boolean) as MemoryRelation[];
    return { memories, relationships };
  }

  async getShowcaseTimeline(): Promise<MemoryDTO[]> {
    const response = camel(await this.request<unknown>("/v1/showcase/timeline"));
    const entries = Array.isArray(response.timeline) ? response.timeline : Array.isArray(response.memories) ? response.memories : [];
    return entries.map(normalizeMemory);
  }

  async createTryWorkspace(): Promise<WorkspaceDTO> {
    const workspace = normalizeWorkspace(await this.request<unknown>("/v1/try", { method: "POST", body: JSON.stringify({}) }));
    this.csrfToken = workspace.csrfToken;
    return workspace;
  }

  async startSession(): Promise<{ sessionId: string; openingMessage?: string | null }> {
    const response = camel(await this.request<unknown>("/v1/sessions", { method: "POST", body: JSON.stringify({}) }));
    const sessionId = str(response.sessionId) || str(response.session_id);
    if (!sessionId) throw new ApiError("The session service returned no session id.", 502, response);
    return { sessionId, openingMessage: str(response.openingMessage) || str(response.opening_message) };
  }

  async sendMessage(sessionId: string, message: string): Promise<{ reply: string; memoryContext: MemoryDTO[]; explainTrace: ExplainTrace | null }> {
    const response = camel(await this.request<unknown>(`/v1/sessions/${encodeURIComponent(sessionId)}/messages`, { method: "POST", body: JSON.stringify({ message }) }));
    const context = Array.isArray(response.memoryContext) ? response.memoryContext : Array.isArray(response.memory_context_used) ? response.memory_context_used : [];
    return { reply: str(response.reply) || "I could not form a reply.", memoryContext: context.map(normalizeMemory), explainTrace: normalizeTrace(response.explainTrace || response.explain_trace) };
  }

  async endSession(sessionId: string, idempotencyKey: string): Promise<EndSessionResult> {
    const response = camel(await this.request<unknown>(`/v1/sessions/${encodeURIComponent(sessionId)}/end`, { method: "POST", headers: { "Idempotency-Key": idempotencyKey }, body: JSON.stringify({}) }));
    const changes = Array.isArray(response.memoryChanges) ? response.memoryChanges : Array.isArray(response.memory_changes) ? response.memory_changes : [];
    return { sessionId: str(response.sessionId) || str(response.session_id) || sessionId, memoryChanges: changes.map(normalizeChange) };
  }
}

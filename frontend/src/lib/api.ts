// Typed fetch client for the Job OS backend.
//
// The base URL defaults to the local backend; override with NEXT_PUBLIC_API_BASE_URL.

import type {
  Application,
  ApplicationCreate,
  ApplicationStatus,
  Job,
  JobCreate,
  JobSource,
  Page,
  Resume,
  ResumeCreate,
  StatusCount,
} from "@/lib/types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "Cannot reach the backend. Is it running on :8000?");
  }

  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const body = await resp.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const api = {
  health: () => request<{ status: string }>("/health"),

  jobs: {
    list: (params?: {
      source?: JobSource;
      company?: string;
      search?: string;
      easy_apply?: boolean;
      offset?: number;
      limit?: number;
    }) => request<Page<Job>>(`/jobs${buildQuery(params)}`),
    get: (id: number) => request<Job>(`/jobs/${id}`),
    create: (body: JobCreate) => request<Job>("/jobs", { method: "POST", ...json(body) }),
    remove: (id: number) => request<{ detail: string }>(`/jobs/${id}`, { method: "DELETE" }),
  },

  resumes: {
    list: (params?: { is_base?: boolean; search?: string; offset?: number; limit?: number }) =>
      request<Page<Resume>>(`/resumes${buildQuery(params)}`),
    create: (body: ResumeCreate) =>
      request<Resume>("/resumes", { method: "POST", ...json(body) }),
    remove: (id: number) =>
      request<{ detail: string }>(`/resumes/${id}`, { method: "DELETE" }),
  },

  applications: {
    list: (params?: {
      status?: ApplicationStatus;
      job_id?: number;
      search?: string;
      offset?: number;
      limit?: number;
    }) => request<Page<Application>>(`/applications${buildQuery(params)}`),
    counts: () => request<StatusCount[]>("/applications/counts"),
    create: (body: ApplicationCreate) =>
      request<Application>("/applications", { method: "POST", ...json(body) }),
    setStatus: (id: number, status: ApplicationStatus) =>
      request<Application>(`/applications/${id}/status`, { method: "PUT", ...json({ status }) }),
    remove: (id: number) =>
      request<{ detail: string }>(`/applications/${id}`, { method: "DELETE" }),
  },
};

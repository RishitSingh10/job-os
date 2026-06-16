// TypeScript mirrors of the backend API schemas (see backend/api/schemas/*).

export type JobSource = "linkedin" | "indeed" | "glassdoor" | "exa" | "manual";

export type ApplicationStatus =
  | "saved"
  | "interested"
  | "tailored"
  | "ready"
  | "pending_approval"
  | "applied"
  | "oa"
  | "interview"
  | "final_round"
  | "offer"
  | "rejected";

export const APPLICATION_STATUSES: ApplicationStatus[] = [
  "saved",
  "interested",
  "tailored",
  "ready",
  "pending_approval",
  "applied",
  "oa",
  "interview",
  "final_round",
  "offer",
  "rejected",
];

export const JOB_SOURCES: JobSource[] = ["linkedin", "indeed", "glassdoor", "exa", "manual"];

export interface Page<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface Job {
  id: number;
  title: string;
  company: string;
  location: string | null;
  salary: string | null;
  url: string;
  easy_apply: boolean;
  description: string;
  source: JobSource;
  external_id: string | null;
  posted_at: string | null;
  dedup_hash: string;
  embedding_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobCreate {
  title: string;
  company: string;
  url: string;
  location?: string | null;
  salary?: string | null;
  easy_apply?: boolean;
  description?: string;
  source?: JobSource;
}

export interface Resume {
  id: number;
  name: string;
  file_type: "pdf" | "docx";
  source_filename: string;
  file_path: string;
  content: string;
  sections: Record<string, unknown>[];
  embedding_id: string | null;
  is_base: boolean;
  created_at: string;
  updated_at: string;
}

export interface ResumeCreate {
  name: string;
  content?: string;
  is_base?: boolean;
}

export interface Application {
  id: number;
  job_id: number;
  resume_id: number | null;
  tailored_resume_id: number | null;
  cover_letter_id: number | null;
  status: ApplicationStatus;
  notes: string;
  tags: string[];
  applied_at: string | null;
  created_at: string;
  updated_at: string;
  job: Job | null;
}

export interface ApplicationCreate {
  job_id: number;
  notes?: string;
  tags?: string[];
  status?: ApplicationStatus;
}

export interface StatusCount {
  status: ApplicationStatus;
  count: number;
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api";
import type { JobCreate, JobSource } from "@/lib/types";

interface JobFilters {
  search?: string;
  source?: JobSource;
  easy_apply?: boolean;
}

export function useJobs(filters: JobFilters = {}) {
  return useQuery({
    queryKey: ["jobs", filters],
    queryFn: () => api.jobs.list({ ...filters, limit: 100 }),
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: JobCreate) => api.jobs.create(body),
    onSuccess: (job) => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      toast.success(`Saved “${job.title}” at ${job.company}`);
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.jobs.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Job deleted");
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
}

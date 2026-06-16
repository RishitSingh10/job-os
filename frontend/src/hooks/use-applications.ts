import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api";
import type { ApplicationCreate, ApplicationStatus } from "@/lib/types";

export function useApplications(status?: ApplicationStatus) {
  return useQuery({
    queryKey: ["applications", { status: status ?? null }],
    queryFn: () => api.applications.list({ status, limit: 200 }),
  });
}

export function useApplicationCounts() {
  return useQuery({
    queryKey: ["applications", "counts"],
    queryFn: () => api.applications.counts(),
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ApplicationCreate) => api.applications.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      toast.success("Application created");
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
}

export function useSetApplicationStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: ApplicationStatus }) =>
      api.applications.setStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      toast.success("Status updated");
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
}

export function useDeleteApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.applications.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      toast.success("Application deleted");
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
}

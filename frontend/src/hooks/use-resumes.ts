import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api";
import type { ResumeCreate } from "@/lib/types";

export function useResumes(search?: string) {
  return useQuery({
    queryKey: ["resumes", { search: search ?? "" }],
    queryFn: () => api.resumes.list({ search, limit: 100 }),
  });
}

export function useCreateResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ResumeCreate) => api.resumes.create(body),
    onSuccess: (resume) => {
      qc.invalidateQueries({ queryKey: ["resumes"] });
      toast.success(`Added resume “${resume.name}”`);
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
}

export function useDeleteResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.resumes.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resumes"] });
      toast.success("Resume deleted");
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
}

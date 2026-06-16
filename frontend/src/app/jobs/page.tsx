"use client";

import { ExternalLink, Search, Send, Trash2 } from "lucide-react";
import { useState } from "react";

import { NewJobDialog } from "@/components/jobs/new-job-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCreateApplication } from "@/hooks/use-applications";
import { useDeleteJob, useJobs } from "@/hooks/use-jobs";
import { formatDate, titleCase } from "@/lib/format";
import { JOB_SOURCES, type JobSource } from "@/lib/types";

const ALL = "all";

export default function JobsPage() {
  const [search, setSearch] = useState("");
  const [source, setSource] = useState<string>(ALL);

  const { data, isLoading, isError, error } = useJobs({
    search: search || undefined,
    source: source === ALL ? undefined : (source as JobSource),
  });
  const deleteJob = useDeleteJob();
  const createApplication = useCreateApplication();

  const jobs = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-56">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search title, company, description…"
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select
          value={source}
          onValueChange={(v) => setSource(v ?? ALL)}
          items={[
            { value: ALL, label: "All sources" },
            ...JOB_SOURCES.map((s) => ({ value: s, label: titleCase(s) })),
          ]}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All sources</SelectItem>
            {JOB_SOURCES.map((s) => (
              <SelectItem key={s} value={s}>
                {titleCase(s)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <NewJobDialog />
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Added</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 6 }).map((__, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))}

            {isError && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-destructive">
                  {(error as Error).message}
                </TableCell>
              </TableRow>
            )}

            {!isLoading && !isError && jobs.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  No jobs yet. Add your first posting.
                </TableCell>
              </TableRow>
            )}

            {jobs.map((job) => (
              <TableRow key={job.id}>
                <TableCell className="font-medium">
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 hover:underline"
                  >
                    {job.title}
                    <ExternalLink className="h-3 w-3 text-muted-foreground" />
                  </a>
                  {job.easy_apply && (
                    <Badge variant="secondary" className="ml-2">
                      Easy Apply
                    </Badge>
                  )}
                </TableCell>
                <TableCell>{job.company}</TableCell>
                <TableCell className="text-muted-foreground">{job.location ?? "—"}</TableCell>
                <TableCell>
                  <Badge variant="outline">{titleCase(job.source)}</Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDate(job.created_at)}</TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    title="Track this job"
                    onClick={() => createApplication.mutate({ job_id: job.id })}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    title="Delete"
                    onClick={() => deleteJob.mutate(job.id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {data && (
        <p className="text-xs text-muted-foreground">
          {data.total} job{data.total === 1 ? "" : "s"}
        </p>
      )}
    </div>
  );
}

"use client";

import { Trash2 } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import {
  useApplications,
  useDeleteApplication,
  useSetApplicationStatus,
} from "@/hooks/use-applications";
import { formatDate, statusLabel } from "@/lib/format";
import { APPLICATION_STATUSES, type ApplicationStatus } from "@/lib/types";

const ALL = "all";

export default function ApplicationsPage() {
  const [filter, setFilter] = useState<string>(ALL);
  const { data, isLoading, isError, error } = useApplications(
    filter === ALL ? undefined : (filter as ApplicationStatus),
  );
  const setStatus = useSetApplicationStatus();
  const remove = useDeleteApplication();

  const apps = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Select
          value={filter}
          onValueChange={(v) => setFilter(v ?? ALL)}
          items={[
            { value: ALL, label: "All statuses" },
            ...APPLICATION_STATUSES.map((s) => ({ value: s, label: statusLabel(s) })),
          ]}
        >
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            {APPLICATION_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {statusLabel(s)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {data && (
          <span className="text-xs text-muted-foreground">
            {data.total} application{data.total === 1 ? "" : "s"}
          </span>
        )}
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Role</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Tags</TableHead>
              <TableHead>Applied</TableHead>
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

            {!isLoading && !isError && apps.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  No applications. Track a job from the Jobs page to get started.
                </TableCell>
              </TableRow>
            )}

            {apps.map((app) => (
              <TableRow key={app.id}>
                <TableCell className="font-medium">{app.job?.title ?? `Job #${app.job_id}`}</TableCell>
                <TableCell>{app.job?.company ?? "—"}</TableCell>
                <TableCell>
                  <Select
                    value={app.status}
                    onValueChange={(v) =>
                      v && setStatus.mutate({ id: app.id, status: v as ApplicationStatus })
                    }
                    items={APPLICATION_STATUSES.map((s) => ({ value: s, label: statusLabel(s) }))}
                  >
                    <SelectTrigger className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {APPLICATION_STATUSES.map((s) => (
                        <SelectItem key={s} value={s}>
                          {statusLabel(s)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {app.tags.length === 0 ? (
                      <span className="text-muted-foreground">—</span>
                    ) : (
                      app.tags.map((t) => (
                        <Badge key={t} variant="secondary">
                          {t}
                        </Badge>
                      ))
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDate(app.applied_at)}</TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    title="Delete"
                    onClick={() => remove.mutate(app.id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

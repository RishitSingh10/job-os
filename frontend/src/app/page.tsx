"use client";

import { Briefcase, FileText, Send, Trophy } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApplicationCounts } from "@/hooks/use-applications";
import { useJobs } from "@/hooks/use-jobs";
import { useResumes } from "@/hooks/use-resumes";
import { statusLabel } from "@/lib/format";

function StatCard({
  label,
  value,
  icon: Icon,
  loading,
}: {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  loading: boolean;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <div className="text-3xl font-bold tabular-nums">{value}</div>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const jobs = useJobs();
  const resumes = useResumes();
  const counts = useApplicationCounts();

  const countMap = new Map((counts.data ?? []).map((c) => [c.status, c.count]));
  const totalApplications = (counts.data ?? []).reduce((sum, c) => sum + c.count, 0);
  const offers = countMap.get("offer") ?? 0;

  const chartData = (counts.data ?? [])
    .filter((c) => c.status !== "rejected")
    .map((c) => ({ name: statusLabel(c.status), count: c.count }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Jobs"
          value={jobs.data?.total ?? 0}
          icon={Briefcase}
          loading={jobs.isLoading}
        />
        <StatCard
          label="Applications"
          value={totalApplications}
          icon={Send}
          loading={counts.isLoading}
        />
        <StatCard
          label="Resumes"
          value={resumes.data?.total ?? 0}
          icon={FileText}
          loading={resumes.isLoading}
        />
        <StatCard label="Offers" value={offers} icon={Trophy} loading={counts.isLoading} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Application pipeline</CardTitle>
        </CardHeader>
        <CardContent className="h-80">
          {counts.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : totalApplications === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              No applications yet. Add jobs and start tracking to see your funnel.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: -16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
                  interval={0}
                  angle={-30}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--popover)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    color: "var(--popover-foreground)",
                  }}
                  cursor={{ fill: "var(--accent)", opacity: 0.3 }}
                />
                <Bar dataKey="count" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

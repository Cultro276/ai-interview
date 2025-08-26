"use client";
import { useDashboard } from "@/context/DashboardContext";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";
import { Users, TimerReset, CheckCircle2, Briefcase, MessageSquare } from "lucide-react";

type Weekly = { interviews_created_7d:number; interviews_completed_7d:number };
type Leader = { interview_id:number; candidate_id:number; candidate_name:string|null; overall_score:number|null };

export default function DashboardPage() {
  const { candidates, jobs, interviews, loading, refreshData } = useDashboard();

  const [weekly, setWeekly] = useState<Weekly | null>(null);
  const [leaders, setLeaders] = useState<Record<number, Leader[]>>({});

  useEffect(() => {
    (async ()=>{
      try { const w = await apiFetch<Weekly>("/api/v1/metrics/weekly"); setWeekly(w); } catch {}
      // Preload leaderboards for latest up to 3 jobs
      try {
        const topJobs = jobs.slice(0, 3);
        const entries = await Promise.all(topJobs.map(j => apiFetch<Leader[]>(`/api/v1/jobs/${j.id}/leaderboard`)));
        const mapped: Record<number, Leader[]> = {};
        topJobs.forEach((j, idx) => { mapped[j.id] = entries[idx] || []; });
        setLeaders(mapped);
      } catch {}
    })();
  }, [jobs.length]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-300">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-neutral-100">Dashboard</h1>
        <Button onClick={refreshData}>Yenile</Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card className="shadow border border-gray-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400">
                <Users className="w-6 h-6" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Total Candidates</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-neutral-100">{candidates.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow border border-gray-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-teal-100 dark:bg-teal-900/30 rounded-lg text-teal-600 dark:text-teal-400">
                <TimerReset className="w-6 h-6" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-300">7 Gün Yeni</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-neutral-100">{weekly?.interviews_created_7d ?? "—"}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow border border-gray-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg text-amber-600 dark:text-amber-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-300">7 Gün Tamamlanan</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-neutral-100">{weekly?.interviews_completed_7d ?? "—"}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow border border-gray-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg text-green-600 dark:text-green-400">
                <Briefcase className="w-6 h-6" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Active Jobs</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-neutral-100">{jobs.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow border border-gray-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg text-purple-600 dark:text-purple-400">
                <MessageSquare className="w-6 h-6" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Total Interviews</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-neutral-100">{interviews.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow border border-gray-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg text-orange-600 dark:text-orange-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Completed</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-neutral-100">{interviews.filter(i => i.status === "completed").length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline (funnel) */}
      <Card className="bg-white dark:bg-neutral-900 shadow border border-gray-200 dark:border-neutral-800 mb-8">
        <CardHeader className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100">Süreç Özeti</h3>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="rounded-lg p-4 border border-gray-100 dark:border-neutral-800">
              <div className="text-sm text-gray-500 dark:text-gray-300">Adaylar</div>
              <div className="text-2xl font-semibold text-gray-900 dark:text-neutral-100">{candidates.length}</div>
            </div>
            <div className="rounded-lg p-4 border border-gray-100 dark:border-neutral-800">
              <div className="text-sm text-gray-500 dark:text-gray-300">Görüşmeler</div>
              <div className="text-2xl font-semibold text-gray-900 dark:text-neutral-100">{interviews.length}</div>
            </div>
            <div className="rounded-lg p-4 border border-gray-100 dark:border-neutral-800">
              <div className="text-sm text-gray-500 dark:text-gray-300">Tamamlanan</div>
              <div className="text-2xl font-semibold text-gray-900 dark:text-neutral-100">{interviews.filter(i => i.status === "completed").length}</div>
            </div>
            <div className="rounded-lg p-4 border border-gray-100 dark:border-neutral-800">
              <div className="text-sm text-gray-500 dark:text-gray-300">7 Gün Tamamlanan</div>
              <div className="text-2xl font-semibold text-gray-900 dark:text-neutral-100">{weekly?.interviews_completed_7d ?? "—"}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Interviews */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg shadow border border-gray-200 dark:border-neutral-800 mb-8">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-neutral-800">
          <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100">Son Görüşmeler</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-neutral-800">
            <thead className="bg-gray-50 dark:bg-neutral-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Candidate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Job
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Recording
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-neutral-900 divide-y divide-gray-200 dark:divide-neutral-800">
              {interviews.slice(0, 5).map((interview) => {
                const candidate = candidates.find(c => c.id === interview.candidate_id);
                const job = jobs.find(j => j.id === interview.job_id);
                return (
                  <tr key={interview.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-neutral-100">
                      {candidate?.name || "Unknown"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                      {job?.title || "Unknown"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        interview.status === "completed" 
                          ? "bg-green-100 text-green-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}>
                        {interview.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                      {new Date(interview.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                      <div className="flex space-x-2">
                        {interview.audio_url && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Audio ✓
                          </span>
                        )}
                        {interview.video_url && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            Video ✓
                          </span>
                        )}
                        {!interview.audio_url && !interview.video_url && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            No Recording
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Job leaderboards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {jobs.slice(0, 3).map(job => (
          <Card key={job.id} className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-300">İş</div>
                  <div className="text-base font-semibold text-gray-900 dark:text-neutral-100">{job.title}</div>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">Top 5</div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <ul className="divide-y divide-gray-200 dark:divide-neutral-800">
                {(leaders[job.id] || []).slice(0, 5).map((row) => (
                  <li key={row.interview_id} className="px-4 py-3 flex items-center justify-between text-sm">
                    <span className="truncate max-w-[70%] text-gray-900 dark:text-neutral-100">{row.candidate_name || `#${row.candidate_id}`}</span>
                    <span className="text-gray-700 dark:text-gray-300">{row.overall_score ?? "—"}</span>
                  </li>
                ))}
                {(!leaders[job.id] || leaders[job.id].length === 0) && (
                  <li className="px-4 py-6 text-sm text-gray-500 dark:text-gray-400">Veri yok</li>
                )}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
} 
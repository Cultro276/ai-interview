"use client";
import { useDashboard } from "@/context/DashboardContext";
import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/context/ToastContext";

export default function ReportsPage() {
  const { candidates, jobs, interviews, loading } = useDashboard();
  const { error: toastError, success } = useToast();
  const [selectedJobId, setSelectedJobId] = useState<number | "all">("all");
  const [order, setOrder] = useState<"desc" | "asc">("desc");
  const [onlyCompleted, setOnlyCompleted] = useState(true);
  const [analysisCache, setAnalysisCache] = useState<Record<number, any>>({});

  const interviewsEnriched = useMemo(() => {
    return interviews.map((iv) => {
      const cand = candidates.find((c) => c.id === iv.candidate_id);
      const job = jobs.find((j) => j.id === iv.job_id);
      const overall = (iv as any)?.overall_score ?? (iv as any)?.analysis?.overall_score ?? null;
      return { ...iv, candidate: cand, job, overall_score: overall } as any;
    });
  }, [interviews, candidates, jobs]);

  const filtered = useMemo(() => {
    const arr = interviewsEnriched
      .filter((iv: any) => selectedJobId === "all" || iv.job_id === selectedJobId)
      .filter((iv: any) => (onlyCompleted ? iv.status === "completed" : true))
      .map((iv: any) => {
        const a = analysisCache[iv.id];
        return a
          ? {
              ...iv,
              overall_score: a.overall_score,
              communication_score: a.communication_score,
              technical_score: a.technical_score,
              cultural_fit_score: a.cultural_fit_score,
              _recommendation: a.overall_score != null ? (a.overall_score >= 75 ? "Proceed" : a.overall_score >= 60 ? "Consider" : "Review") : null,
            }
          : iv;
      });
    arr.sort((a: any, b: any) => {
      const sa = typeof a.overall_score === "number" ? a.overall_score : -1;
      const sb = typeof b.overall_score === "number" ? b.overall_score : -1;
      return order === "desc" ? sb - sa : sa - sb;
    });
    return arr;
  }, [interviewsEnriched, selectedJobId, order, onlyCompleted, analysisCache]);

  // Lazy-load analyses for visible interviews
  useEffect(() => {
    const missing = filtered
      .filter((iv: any) => analysisCache[iv.id] === undefined)
      .map((iv: any) => iv.id);
    if (missing.length === 0) return;
    (async () => {
      try {
        const results = await Promise.all(
          missing.map((id) =>
            apiFetch(`/api/v1/conversations/analysis/${id}`).catch(() => null)
          )
        );
        const newCache: Record<number, any> = {};
        missing.forEach((id, idx) => {
          const a = results[idx];
          if (a) newCache[id] = a;
        });
        if (Object.keys(newCache).length) {
          setAnalysisCache((prev) => ({ ...prev, ...newCache }));
        }
      } catch (e: any) {
        // swallow errors; not critical
      }
    })();
  }, [filtered]);

  const exportCsv = () => {
    const header = [
      "InterviewId",
      "Candidate",
      "Job",
      "Overall",
      "Communication",
      "Technical",
      "Culture",
      "Status",
      "CompletedAt",
    ];
    const rows = filtered.map((iv: any) => [
      iv.id,
      iv.candidate?.name || "",
      iv.job?.title || "",
      iv.overall_score ?? "",
      iv.communication_score ?? "",
      iv.technical_score ?? "",
      iv.cultural_fit_score ?? "",
      iv.status,
      iv.completed_at ? new Date(iv.completed_at).toISOString() : "",
    ]);
    const csv = [header, ...rows].map((r) => r.map((c) => `${c}`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = selectedJobId === "all" ? "reports_all_jobs.csv" : `reports_job_${selectedJobId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    success("CSV exported");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading reports...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <div className="flex items-center gap-3">
          <select
            value={selectedJobId as any}
            onChange={(e) => setSelectedJobId(e.target.value === "all" ? "all" : Number(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            <option value="all">All Jobs</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>{j.title}</option>
            ))}
          </select>
          <select
            value={order}
            onChange={(e) => setOrder(e.target.value as any)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            <option value="desc">Best → Worst</option>
            <option value="asc">Worst → Best</option>
          </select>
          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={onlyCompleted} onChange={(e) => setOnlyCompleted(e.target.checked)} />
            Only completed
          </label>
          <button onClick={exportCsv} className="px-3 py-2 text-sm bg-gray-100 text-gray-800 rounded-md hover:bg-gray-200">Export CSV</button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Candidate</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Job</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Overall</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Comm</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tech</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Culture</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Decision</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filtered.map((iv: any) => (
              <tr key={iv.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{iv.candidate?.name || "Unknown"}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{iv.job?.title || "Unknown"}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{iv.overall_score ?? "—"}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{(iv as any)?.communication_score ?? "—"}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{(iv as any)?.technical_score ?? "—"}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{(iv as any)?.cultural_fit_score ?? "—"}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {(() => {
                    const dec = (iv as any)._recommendation;
                    if (!dec) return <span className="text-gray-400">—</span>;
                    const cls = dec === "Proceed" ? "bg-green-100 text-green-800" : dec === "Consider" ? "bg-yellow-100 text-yellow-800" : "bg-rose-100 text-rose-800";
                    return <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${cls}`}>{dec}</span>;
                  })()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    iv.status === "completed" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                  }`}>
                    {iv.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}



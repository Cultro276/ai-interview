"use client";
import { useDashboard } from "@/context/DashboardContext";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function DashboardPage() {
  const { candidates, jobs, interviews, loading, refreshData } = useDashboard();
  const [metrics, setMetrics] = useState<{ upload_p95_ms?: number; analysis_p95_ms?: number; error_rate?: number } | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  
  // Get job statistics
  const getJobStats = (jobId: number) => {
    const jobCandidates = candidates.filter(candidate => 
      interviews.some(interview => 
        interview.job_id === jobId && interview.candidate_id === candidate.id
      )
    );
    const jobInterviews = interviews.filter(interview => interview.job_id === jobId);
    const completedInterviews = jobInterviews.filter(interview => interview.status === "completed");
    
    return {
      totalCandidates: jobCandidates.length,
      totalInterviews: jobInterviews.length,
      completedInterviews: completedInterviews.length,
      pendingInterviews: jobInterviews.length - completedInterviews.length
    };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard Overview</h1>
        <button
          onClick={refreshData}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
        >
          Refresh Data
        </button>
      </div>

      {/* Recruiter-friendly Metrics Row */}
      <div className="bg-white p-6 rounded-lg shadow border border-gray-200 mb-8">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-medium text-gray-900">System Health (Recruiter View)</h3>
          <button
            onClick={async () => {
              setMetricsLoading(true);
              try {
                const data = await apiFetch<{ upload_p95_ms: number; analysis_p95_ms: number; error_rate: number }>("/api/v1/metrics");
                setMetrics(data);
              } catch {
                setMetrics(null);
              } finally {
                setMetricsLoading(false);
              }
            }}
            className="px-3 py-1 text-sm bg-gray-100 text-gray-800 rounded-md hover:bg-gray-200"
          >
            {metricsLoading ? "Loading…" : "Refresh Metrics"}
          </button>
        </div>
        <p className="text-xs text-gray-500 mb-4">Bu değerler, adayların yaşadığı hız ve başarıyı yansıtır: daha düşük süreler ve daha düşük hata oranı = daha pürüzsüz deneyim.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 border border-gray-200 rounded-md">
            <p className="text-sm font-medium text-gray-700">Aday Yükleme Hızı (P95)</p>
            <p className="text-2xl font-semibold text-gray-900">{metrics?.upload_p95_ms != null ? `${Math.round(metrics.upload_p95_ms/1000)} sn` : "—"}</p>
            <p className="text-xs text-gray-500 mt-1">Adayların dosya yüklemeyi %95 olasılıkla bitirdiği süre. Hedef ≤ 10 sn.</p>
          </div>
          <div className="p-4 border border-gray-200 rounded-md">
            <p className="text-sm font-medium text-gray-700">Analiz Tamamlama Süresi (P95)</p>
            <p className="text-2xl font-semibold text-gray-900">{metrics?.analysis_p95_ms != null ? `${Math.round(metrics.analysis_p95_ms/1000)} sn` : "—"}</p>
            <p className="text-xs text-gray-500 mt-1">Mülakat sonrası raporun hazır olma süresi. Hedef ≤ 60 sn.</p>
          </div>
          <div className="p-4 border border-gray-200 rounded-md">
            <p className="text-sm font-medium text-gray-700">Hata Oranı</p>
            <p className="text-2xl font-semibold text-gray-900">{metrics?.error_rate != null ? `${(metrics.error_rate * 100).toFixed(2)}%` : "—"}</p>
            <p className="text-xs text-gray-500 mt-1">Başarısız işlem yüzdesi. Hedef ≤ %1.</p>
          </div>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Candidates</p>
              <p className="text-2xl font-bold text-gray-900">{candidates.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2-2v2m8 0V6a2 2 0 012 2v6a2 2 0 01-2 2H8a2 2 0 01-2-2V8a2 2 0 012-2V6" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Active Jobs</p>
              <p className="text-2xl font-bold text-gray-900">{jobs.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg">
              <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Interviews</p>
              <p className="text-2xl font-bold text-gray-900">{interviews.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center">
            <div className="p-2 bg-orange-100 rounded-lg">
              <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Completed</p>
              <p className="text-2xl font-bold text-gray-900">{interviews.filter(i => i.status === "completed").length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Interviews with Conversation Data */}
      <div className="bg-white rounded-lg shadow border border-gray-200 mb-8">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Recent Interviews</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Candidate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Job
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Recording
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {interviews.slice(0, 5).map((interview) => {
                const candidate = candidates.find(c => c.id === interview.candidate_id);
                const job = jobs.find(j => j.id === interview.job_id);
                return (
                  <tr key={interview.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {candidate?.name || "Unknown"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
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
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(interview.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
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

      {/* Job-specific Statistics */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Job Statistics</h3>
        <div className="space-y-4">
          {jobs.slice(0, 3).map((job) => {
            const stats = getJobStats(job.id);
            return (
              <div key={job.id} className="flex items-center justify-between p-4 border border-gray-100 rounded-lg hover:bg-gray-50">
                <div>
                  <h4 className="font-medium text-gray-900">{job.title}</h4>
                  <p className="text-sm text-gray-500 truncate max-w-md">{job.description}</p>
                </div>
                <div className="flex items-center space-x-4 text-sm">
                  <span className="text-blue-600">{stats.totalCandidates} candidates</span>
                  <span className="text-green-600">{stats.completedInterviews} completed</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
} 
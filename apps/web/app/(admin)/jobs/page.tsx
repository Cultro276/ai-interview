"use client";
import { useDashboard } from "@/context/DashboardContext";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/EmptyState";

export default function JobsPage() {
  const { jobs, candidates, interviews, loading } = useDashboard();

  // Compute AI score per candidate (from interviews' analysis not directly here; keep placeholder 0)
  const interviewByCandidate = useMemo(() => {
    const map = new Map<number, any>();
    for (const i of interviews) {
      map.set(i.candidate_id, i);
    }
    return map;
  }, [interviews]);

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
      pendingInterviews: jobInterviews.length - completedInterviews.length,
      jobCandidates,
    };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading jobs...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Job Positions</h1>
        <Link href="/jobs/new">
          <Button>Create New Job</Button>
        </Link>
      </div>
      {jobs.length === 0 && (
        <EmptyState title="No jobs yet" description="Create your first job to invite candidates and start interviewing." actionLabel="Create Job" onAction={() => (window.location.href = "/jobs/new")} />
      )}
      <div className="grid gap-6">
        {jobs.map((job) => {
          const stats = getJobStats(job.id);
          // Sort candidates by completed first while waiting for leaderboard API
          const sortedCandidates = [...stats.jobCandidates].sort((a, b) => {
            const ia = interviewByCandidate.get(a.id);
            const ib = interviewByCandidate.get(b.id);
            const sa = ia && ia.status === "completed" ? 1 : 0;
            const sb = ib && ib.status === "completed" ? 1 : 0;
            return sb - sa;
          });
          return (
            <div key={job.id} className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex justify_between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{job.title}</h3>
                  <p className="text-gray-600 mt-1">{job.description}</p>
                  <p className="text-sm text-gray-500 mt-2">
                    Created: {new Date(job.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex space-x-2">
                  <Link href={`/jobs/${job.id}/candidates`}>
                    <Button variant="outline" size="sm">View Candidates</Button>
                  </Link>
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button variant="ghost" size="sm">Edit</Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Edit Job</DialogTitle>
                      </DialogHeader>
                      <form className="space-y-3" onSubmit={async (e)=>{
                        e.preventDefault();
                        const form = e.target as HTMLFormElement;
                        const title = (form.elements.namedItem('title') as HTMLInputElement).value;
                        const description = (form.elements.namedItem('description') as HTMLTextAreaElement).value;
                        try {
                          await apiFetch(`/api/v1/jobs/${job.id}`, { method: 'PUT', body: JSON.stringify({ title, description }) });
                          window.location.reload();
                        } catch (err) {
                          alert((err as any)?.message || 'Update failed');
                        }
                      }}>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                          <input name="title" defaultValue={job.title} className="w-full px-3 py-2 border border-gray-300 rounded-md" />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                          <textarea name="description" defaultValue={job.description} rows={6} className="w-full px-3 py-2 border border-gray-300 rounded-md" />
                        </div>
                        <div className="flex justify-end">
                          <Button type="submit">Save</Button>
                        </div>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </div>
              {/* Candidate list preview sorted */}
              {sortedCandidates.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Top Candidates</h4>
                  <ul className="space-y-1 text-sm text-gray-700">
                    {sortedCandidates.slice(0, 5).map((c) => (
                      <li key={c.id} className="flex justify-between">
                        <span>{c.name}</span>
                        <span className="text-xs text-gray-500">{interviewByCandidate.get(c.id)?.status === "completed" ? "completed" : "pending"}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div className="grid grid-cols-4 gap-4 pt-4 border-t border-gray-100">
                <div className="text-center">
                  <p className="text-2xl font-bold text-brand-600">{stats.totalCandidates}</p>
                  <p className="text-sm text-gray-500">Candidates</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-green-600">{stats.totalInterviews}</p>
                  <p className="text-sm text-gray-500">Interviews</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-purple-600">{stats.completedInterviews}</p>
                  <p className="text-sm text-gray-500">Completed</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-orange-600">{stats.pendingInterviews}</p>
                  <p className="text-sm text-gray-500">Pending</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
} 
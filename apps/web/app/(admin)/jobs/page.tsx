"use client";
import { useDashboard } from "@/context/DashboardContext";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogClose } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/context/ToastContext";

export default function JobsPage() {
  const { jobs, candidates, interviews, loading, refreshData } = useDashboard();
  const { error: toastError } = useToast();

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
      <div>
        <div className="flex justify-between items-center mb-6">
          <div className="h-8 w-48"><Skeleton className="h-8 w-48" /></div>
          <div className="h-9 w-32"><Skeleton className="h-9 w-32" /></div>
        </div>
        <div className="grid gap-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-lg p-6">
              <div className="flex justify-between items-start mb-4">
                <div className="space-y-2">
                  <Skeleton className="h-5 w-64" />
                  <Skeleton className="h-4 w-[80%]" />
                  <Skeleton className="h-4 w-40" />
                </div>
                <div className="flex space-x-2">
                  <Skeleton className="h-8 w-28" />
                  <Skeleton className="h-8 w-20" />
                </div>
              </div>
              <div className="grid grid-cols-4 gap-4 pt-4 border-t border-gray-100 dark:border-neutral-800">
                {Array.from({ length: 4 }).map((__, j) => (
                  <div key={j} className="text-center space-y-2">
                    <Skeleton className="h-6 w-10 mx-auto" />
                    <Skeleton className="h-3 w-20 mx-auto" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-neutral-100">İş İlanları</h1>
        <Link href="/jobs/new">
          <Button>Yeni İş Oluştur</Button>
        </Link>
      </div>
      {jobs.length === 0 && (
        <EmptyState title="Henüz iş ilanı yok" description="Aday davet etmek ve mülakatlara başlamak için ilk ilanınızı oluşturun." actionLabel="İlan Oluştur" onAction={() => (window.location.href = "/jobs/new")} />
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
            <div key={job.id} className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-lg p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-neutral-100">{job.title}</h3>
                  <p className="text-gray-600 dark:text-gray-300 mt-1">{job.description}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                    Created: {new Date(job.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex space-x-2">
                  <Link href={`/jobs/${job.id}/candidates`} aria-label={`${job.title} ilanı adaylarını görüntüle`}>
                    <Button variant="outline" size="sm">Adayları Görüntüle</Button>
                  </Link>
                  {/* Editor deprecated; hide link */}
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button variant="ghost" size="sm">Düzenle</Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogTitle id={`edit-job-title-${job.id}`}>İşi Düzenle</DialogTitle>
                      <DialogDescription id={`edit-job-desc-${job.id}`}>
                        Başlığı ve açıklamayı güncelleyin, ardından kaydedin.
                      </DialogDescription>
                      <form className="space-y-3" onSubmit={async (e)=>{
                        e.preventDefault();
                        const form = e.target as HTMLFormElement;
                        const title = (form.elements.namedItem('title') as HTMLInputElement).value;
                        const description = (form.elements.namedItem('description') as HTMLTextAreaElement).value;
                        try {
                          await apiFetch(`/api/v1/jobs/${job.id}`, { method: 'PUT', body: JSON.stringify({ title, description }) });
                          await refreshData();
                        } catch (err) {
                          toastError((err as any)?.message || 'Update failed');
                        }
                      }}>
                        <div>
                          <label htmlFor={`title-${job.id}`} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Başlık</label>
                          <input id={`title-${job.id}`} name="title" defaultValue={job.title} className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600" />
                        </div>
                        <div>
                          <label htmlFor={`description-${job.id}`} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Açıklama</label>
                          <textarea id={`description-${job.id}`} name="description" defaultValue={job.description} rows={6} className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600" />
                        </div>
                        <div className="flex justify-end">
                          <Button type="submit">Kaydet</Button>
                        </div>
                      </form>
                    </DialogContent>
                  </Dialog>
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button variant="ghost" size="sm" aria-label="İlanı sil">✕</Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>İlanı kaldırmak istiyor musunuz?</DialogTitle>
                        <DialogDescription>Bu işlem geri alınamaz.</DialogDescription>
                      </DialogHeader>
                      <div className="flex justify-end gap-2">
                        <DialogClose asChild>
                          <Button variant="outline">Vazgeç</Button>
                        </DialogClose>
                        <Button
                          variant="destructive"
                          onClick={async () => {
                            try {
                              await apiFetch(`/api/v1/jobs/${job.id}`, { method: 'DELETE' });
                              await refreshData();
                            } catch (err) {
                              toastError((err as any)?.message || 'Silme başarısız');
                            }
                          }}
                        >Sil</Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </div>
              {/* Candidate list preview sorted */}
              {sortedCandidates.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Öne Çıkan Adaylar</h4>
                  <ul className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
                    {sortedCandidates.slice(0, 5).map((c) => (
                      <li key={c.id} className="flex justify-between">
                        <span>{c.name}</span>
                        <span className="text-xs text-gray-500">{interviewByCandidate.get(c.id)?.status === "completed" ? "completed" : "pending"}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div className="grid grid-cols-4 gap-4 pt-4 border-t border-gray-100 dark:border-neutral-800">
                <div className="text-center">
                  <p className="text-2xl font-bold text-brand-600">{stats.totalCandidates}</p>
                  <p className="text-sm text-gray-500">Aday</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-green-600">{stats.totalInterviews}</p>
                  <p className="text-sm text-gray-500">Mülakat</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-purple-600">{stats.completedInterviews}</p>
                  <p className="text-sm text-gray-500">Tamamlanan</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-orange-600">{stats.pendingInterviews}</p>
                  <p className="text-sm text-gray-500">Bekleyen</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
} 
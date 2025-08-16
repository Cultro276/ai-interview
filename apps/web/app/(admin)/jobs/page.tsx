"use client";
import { useDashboard } from "@/context/DashboardContext";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/context/ToastContext";

export default function JobsPage() {
	const { jobs, candidates, interviews, loading, refreshData } = useDashboard();
	const { success, error: toastError } = useToast();
	const [query, setQuery] = useState("");
	const [editingId, setEditingId] = useState<number | null>(null);
	const [editTitle, setEditTitle] = useState("");
	const [editDescription, setEditDescription] = useState("");
	const [saving, setSaving] = useState(false);

	// Persist search query for employer productivity
	useEffect(() => {
		if (typeof window === "undefined") return;
		const saved = localStorage.getItem("jobs:query");
		if (saved) setQuery(saved);
	}, []);
	useEffect(() => {
		if (typeof window === "undefined") return;
		localStorage.setItem("jobs:query", query);
	}, [query]);

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
					<div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
					<p className="text-gray-600">Loading jobs...</p>
				</div>
			</div>
		);
	}

	const filteredJobs = jobs.filter(j => {
		if (!query.trim()) return true;
		const q = query.toLowerCase();
		return j.title.toLowerCase().includes(q) || (j.description || "").toLowerCase().includes(q);
	});

	return (
		<div>
			<div className="flex justify-between items-center mb-6">
				<h1 className="text-2xl font-bold text-gray-900">Job Positions</h1>
				<div className="flex items-center gap-3">
					<input
						value={query}
						onChange={(e) => setQuery(e.target.value)}
						placeholder="Search jobs..."
						className="px-3 py-2 border border-gray-300 rounded-md text-sm"
					/>
					<Link
						href="/jobs/new"
						className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
					>
						Create New Job
					</Link>
				</div>
			</div>
			
			<div className="grid gap-6">
				{filteredJobs.map((job) => {
					const stats = getJobStats(job.id);
					// Sort candidates by a proxy score (completed interviews first). For real AI score, would need analysis aggregation API.
					const sortedCandidates = [...stats.jobCandidates].sort((a, b) => {
						const ia = interviewByCandidate.get(a.id);
						const ib = interviewByCandidate.get(b.id);
						const sa = ia && ia.status === "completed" ? 1 : 0;
						const sb = ib && ib.status === "completed" ? 1 : 0;
						return sb - sa;
					});
					return (
						<div key={job.id} className="bg-white border border-gray-200 rounded-lg p-6">
							<div className="flex justify-between items-start mb-4">
								<div>
									<h3 className="text-lg font-semibold text-gray-900">{job.title}</h3>
									<p className="text-gray-600 mt-1">{job.description}</p>
									<p className="text-sm text-gray-500 mt-2">
										Created: {new Date(job.created_at).toLocaleDateString()}
									</p>
								</div>
								<div className="flex space-x-2">
									<a href={`/jobs/${job.id}/candidates`} className="px-3 py-1 text-blue-600 border border-blue-600 rounded hover:bg-blue-50">
										View Candidates
									</a>
									<a href={`/reports?job=${job.id}`} className="px-3 py-1 text-indigo-600 border border-indigo-600 rounded hover:bg-indigo-50">
										View Report
									</a>
									<button
										className="px-3 py-1 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
										onClick={() => {
											setEditingId(job.id);
											setEditTitle(job.title);
											setEditDescription(job.description || "");
										}}
									>
										Edit
									</button>
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
									<p className="text-2xl font-bold text-blue-600">{stats.totalCandidates}</p>
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

			{/* Edit Modal */}
			{editingId !== null && (
				<div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center">
					<div className="bg-white rounded-lg shadow-lg border border-gray-200 w-full max-w-lg p-6">
						<h3 className="text-lg font-semibold text-gray-900 mb-4">Edit Job</h3>
						<div className="space-y-4">
							<div>
								<label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
								<input
									value={editTitle}
									onChange={(e) => setEditTitle(e.target.value)}
									className="w-full px-3 py-2 border border-gray-300 rounded-md"
								/>
							</div>
							<div>
								<label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
								<textarea
									value={editDescription}
									onChange={(e) => setEditDescription(e.target.value)}
									rows={8}
									className="w-full px-3 py-2 border border-gray-300 rounded-md"
								/>
							</div>
						</div>
						<div className="flex justify-end gap-3 mt-6">
							<button
								className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
								onClick={() => setEditingId(null)}
								disabled={saving}
							>
								Cancel
							</button>
							<button
								className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
								onClick={async () => {
									if (!editTitle.trim()) {
										toastError("Title is required");
										return;
									}
									setSaving(true);
									try {
										await apiFetch(`/api/v1/jobs/${editingId}`, {
											method: "PUT",
											body: JSON.stringify({ title: editTitle, description: editDescription }),
										});
										await refreshData();
										success("Job updated");
										setEditingId(null);
									} catch (e: any) {
										toastError(e.message || "Update failed");
									} finally {
										setSaving(false);
									}
								}}
								disabled={saving}
							>
								{saving ? "Saving…" : "Save"}
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
} 
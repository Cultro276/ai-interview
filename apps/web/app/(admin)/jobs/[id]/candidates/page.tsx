"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { useDashboard } from "@/context/DashboardContext";
import { apiFetch } from "@/lib/api";

export default function JobCandidatesPage() {
  const params = useParams();
  const jobId = Number(params?.id);
  const { candidates, interviews, loading, refreshData } = useDashboard();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [expiresDays, setExpiresDays] = useState(7);
  const [singleFile, setSingleFile] = useState<File | null>(null);
  const [singleName, setSingleName] = useState("");
  const [singleEmail, setSingleEmail] = useState("");
  const [creating, setCreating] = useState(false);
  const [singleExpiry, setSingleExpiry] = useState(7);

  const jobCandidateIds = interviews
    .filter((i) => i.job_id === jobId)
    .map((i) => i.candidate_id);
  const jobCandidates = candidates.filter((c) => jobCandidateIds.includes(c.id));

  const onUpload = async () => {
    if (!files.length) return;
    setUploading(true);
    try {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      form.append("expires_in_days", String(expiresDays));
      await apiFetch(`/api/v1/jobs/${jobId}/candidates/bulk-upload`, {
        method: "POST",
        body: form,
      });
      await refreshData();
      alert("Upload completed.");
    } catch (e: any) {
      alert(e.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const isValidEmail = (email: string) => /.+@.+\..+/.test(email);

  const createSingleCandidate = async () => {
    if (!singleName || !singleEmail) {
      alert("Name and Email are required");
      return;
    }
    if (!isValidEmail(singleEmail)) {
      alert("Please enter a valid email address");
      return;
    }
    setCreating(true);
    try {
      const cand = await apiFetch<any>("/api/v1/candidates", {
        method: "POST",
        body: JSON.stringify({ name: singleName, email: singleEmail, expires_in_days: singleExpiry }),
      });
      await apiFetch("/api/v1/interviews", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId, candidate_id: cand.id, status: "pending" }),
      });
      setSingleName("");
      setSingleEmail("");
      await refreshData();
      alert("Candidate created and linked to job.");
    } catch (e: any) {
      alert(e.message || "Create failed");
    } finally {
      setCreating(false);
    }
  };

  const sendLink = async (candId: number) => {
    try {
      await apiFetch(`/api/v1/candidates/${candId}/send-link?expires_in_days=${expiresDays}`, { method: "POST" });
      alert("Link sent (mock)");
    } catch (e: any) {
      alert(e.message);
    }
  };

  const sendAll = async () => {
    try {
      const ids = jobCandidates.map(c => c.id);
      await Promise.all(ids.map(id => apiFetch(`/api/v1/candidates/${id}/send-link?expires_in_days=${expiresDays}`, { method: "POST" })));
      alert("All links sent (mock)");
    } catch (e: any) {
      alert(e.message || "Failed to send all links");
    }
  };

  const downloadCv = async (candId: number) => {
    try {
      const { url } = await apiFetch<{ url: string }>(`/api/v1/candidates/${candId}/resume-download-url`);
      window.open(url, "_blank");
    } catch (e: any) {
      alert(e.message || "Download failed");
    }
  };

  if (loading) return <div className="p-6">Loading…</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Job Candidates</h1>
        <a href="/jobs" className="text-blue-600">← Back to Jobs</a>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-8">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Bulk Upload CVs</h3>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2">
            <input
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.txt"
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
              className="block w-full text-sm text-gray-600"
            />
            {files.length > 0 && (
              <p className="text-sm text-gray-500 mt-2">{files.length} file(s) selected</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Link Expiry (days)</label>
            <input
              type="number"
              min={1}
              max={365}
              value={expiresDays}
              onChange={(e) => setExpiresDays(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            <button
              onClick={sendAll}
              className="mt-2 w-full px-3 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700"
            >
              Send Link to All
            </button>
          </div>
        </div>
        <button
          onClick={onUpload}
          disabled={uploading || files.length === 0}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {uploading ? "Uploading…" : "Upload & Parse"}
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-8">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Create Single Candidate</h3>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              value={singleName}
              onChange={(e) => setSingleName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="Furkan Ünal"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={singleEmail}
              onChange={(e) => setSingleEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="furkan@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Expiry (days)</label>
            <input
              type="number"
              min={1}
              max={365}
              value={singleExpiry}
              onChange={(e) => setSingleExpiry(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
        </div>
        <div className="flex gap-3 mt-4">
          <button
            onClick={createSingleCandidate}
            disabled={creating}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {creating ? "Creating…" : "Create Candidate"}
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Candidates for this Job</h3>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Resume</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {jobCandidates.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{c.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.email}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {c.resume_url ? (
                    <button onClick={() => downloadCv(c.id)} className="text-blue-600 hover:text-blue-800">View CV</button>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => sendLink(c.id)}
                    className="text-blue-600 hover:text-blue-900 mr-4"
                  >
                    Send Link
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
} 
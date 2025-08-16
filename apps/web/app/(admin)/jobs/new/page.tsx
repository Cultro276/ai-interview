"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useDashboard } from "@/context/DashboardContext";

export default function NewJobPage() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const router = useRouter();
  const { refreshData } = useDashboard();
  const submit = async () => {
    if (!title) { alert("Title is required"); return; }
    await apiFetch("/api/v1/jobs", {
      method: "POST",
      body: JSON.stringify({ title, description }),
    });
    await refreshData();
    router.push("/jobs");
  };
  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create New Job</h1>
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Senior Backend Engineer"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Job Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Responsibilities, requirements, nice-to-haves..."
            rows={10}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
          <p className="text-xs text-gray-500 mt-1">Bu açıklama AI analizine bağlam olarak gönderilir.</p>
        </div>
        <div className="flex justify-end">
          <button
            onClick={submit}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Save Job
          </button>
        </div>
      </div>
    </div>
  );
} 
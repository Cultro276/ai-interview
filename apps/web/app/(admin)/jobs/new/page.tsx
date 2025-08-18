"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useDashboard } from "@/context/DashboardContext";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/context/ToastContext";

export default function NewJobPage() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [expiryDays, setExpiryDays] = useState<number>(30);
  const [errors, setErrors] = useState<{ title?: string; description?: string }>({});
  const router = useRouter();
  const { refreshData } = useDashboard();
  const { success, error } = useToast();
  const titleRef = useRef<HTMLInputElement | null>(null);
  const descRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (titleRef.current) titleRef.current.focus();
  }, []);

  const validate = () => {
    const next: { title?: string; description?: string } = {};
    if (!title.trim()) next.title = "Title is required";
    if (description.trim().length > 0 && description.trim().length < 20) next.description = "Description should be at least 20 characters";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async () => {
    if (!validate()) {
      if (errors.title && titleRef.current) titleRef.current.focus();
      else if (errors.description && descRef.current) descRef.current.focus();
      return;
    }
    try {
      await apiFetch("/api/v1/jobs/", {
        method: "POST",
        body: JSON.stringify({ title: title.trim(), description: description.trim(), expires_in_days: expiryDays }),
      });
      await refreshData();
      success("Job created");
      router.push("/jobs");
    } catch (e: any) {
      error(e.message || "Failed to create job");
    }
  };
  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create New Job</h1>
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <div>
          <Label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">Title</Label>
          <Input
            id="title"
            aria-label="Job title"
            aria-invalid={!!errors.title}
            aria-describedby={errors.title ? "title-error" : undefined}
            ref={titleRef}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Senior Backend Engineer"
          />
          {errors.title && (
            <p id="title-error" className="mt-1 text-sm text-red-600">{errors.title}</p>
          )}
        </div>
        <div>
          <Label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">Job Description</Label>
          <textarea
            id="description"
            aria-label="Job description"
            aria-invalid={!!errors.description}
            aria-describedby={errors.description ? "description-error" : undefined}
            ref={descRef}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Responsibilities, requirements, nice-to-haves..."
            rows={10}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          />
          {errors.description && (
            <p id="description-error" className="mt-1 text-sm text-red-600">{errors.description}</p>
          )}
          <p className="text-xs text-gray-500 mt-1">Bu açıklama AI analizine bağlam olarak gönderilir.</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Link Expiry (days)</label>
          <input
            type="number"
            min={1}
            max={365}
            value={expiryDays}
            onChange={(e)=> setExpiryDays(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
          <p className="text-xs text-gray-500 mt-1">Bu değer varsayılan aday daveti süresine kopyalanır.</p>
        </div>
        <div className="flex justify-end">
          <Button onClick={submit} aria-label="Save job">Save Job</Button>
        </div>
      </div>
    </div>
  );
} 
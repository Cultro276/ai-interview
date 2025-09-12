"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useDashboard } from "@/context/DashboardContext";
import { Button, Input, Label } from "@/components/ui";
import { useToast } from "@/context/ToastContext";

export default function NewJobPage() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [extraQuestions, setExtraQuestions] = useState("");
  const [rubricItems, setRubricItems] = useState<Array<{ label: string; weight: number }>>([
    { label: "Problem Çözme", weight: 0.25 },
    { label: "Teknik Yeterlilik", weight: 0.45 },
    { label: "İletişim", weight: 0.15 },
    { label: "Kültür/İş Uygunluğu", weight: 0.15 },
  ]);
  const [expiryDays, setExpiryDays] = useState<number>(30);
  const [errors, setErrors] = useState<{ title?: string; description?: string }>({});
  const [extracting, setExtracting] = useState(false);
  const [autoReqJson, setAutoReqJson] = useState<string>("");
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
    if (!title.trim()) next.title = "Başlık gerekli";
    if (description.trim().length > 0 && description.trim().length < 20) next.description = "Açıklama en az 20 karakter olmalı";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async () => {
    if (!validate()) {
      if (errors.title && titleRef.current) titleRef.current.focus();
      else if (errors.description && descRef.current) descRef.current.focus();
      return;
    }
    // Validate rubric weights sum to 1.0 (±0.01)
    const total = rubricItems.reduce((s, it) => s + (Number(it.weight) || 0), 0);
    if (Math.abs(total - 1.0) > 0.01) {
      error("Rubrik ağırlıkları toplamı 1.0 olmalı");
      return;
    }
    try {
      const rubric_json = JSON.stringify({ criteria: rubricItems.map((it) => ({ label: it.label, weight: Number(it.weight) })) });
      const job = await apiFetch<{ id: number }>("/api/v1/jobs/", {
        method: "POST",
        body: JSON.stringify({ title: title.trim(), description: description.trim(), extra_questions: extraQuestions.trim() || null, expires_in_days: expiryDays, rubric_json }),
      });
      // Extract-requirements endpoint kaldırıldı; istenirse analiz daha sonra yapılır
      await refreshData();
      success("İlan oluşturuldu");
      router.push("/jobs");
    } catch (e: any) {
      error(e.message || "Failed to create job");
    }
  };
  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-neutral-100">Yeni İlan</h1>
        <a href="/jobs" aria-label="Kapat" className="text-gray-500 hover:text-gray-700">✕</a>
      </div>
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <div>
          <Label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">Başlık</Label>
          <Input
            id="title"
            aria-label="Job title"
            aria-invalid={!!errors.title}
            aria-describedby={errors.title ? "title-error" : undefined}
            ref={titleRef}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Kıdemli Backend Mühendisi"
          />
          {errors.title && (
            <p id="title-error" className="mt-1 text-sm text-red-600">{errors.title}</p>
          )}
        </div>
        <div>
          <Label htmlFor="extra_questions" className="block text-sm font-medium text-gray-700 mb-1">Ekstra Sorular (opsiyonel)</Label>
          <textarea
            id="extra_questions"
            aria-label="Extra questions"
            value={extraQuestions}
            onChange={(e) => setExtraQuestions(e.target.value)}
            placeholder={"Her satıra bir soru yazın.\nÖrn: ERP geçişinde rolünüz neydi?\nÖrn: Docker üretim sorununu nasıl çözdünüz?"}
            rows={6}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          />
          <p className="text-xs text-gray-500 mt-1">Bu sorular mülakat sırasında öncelikli olarak sorulacaktır.</p>
        </div>
        <div>
          <Label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">İş Tanımı</Label>
          <textarea
            id="description"
            aria-label="Job description"
            aria-invalid={!!errors.description}
            aria-describedby={errors.description ? "description-error" : undefined}
            ref={descRef}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Sorumluluklar, gereksinimler, artılar..."
            rows={10}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          />
          {errors.description && (
            <p id="description-error" className="mt-1 text-sm text-red-600">{errors.description}</p>
          )}
          <p className="text-xs text-gray-500 mt-1">Bu açıklama AI analizine bağlam olarak gönderilir.</p>
        </div>
        {/* Rubric Tab (simple inline) */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label className="block text-sm font-medium text-gray-700">Rubrik (toplam ağırlık = 1.0)</Label>
            <span className="text-xs text-gray-500">Toplam: {rubricItems.reduce((s, it) => s + (Number(it.weight) || 0), 0).toFixed(2)}</span>
          </div>
          <div className="space-y-2">
            {rubricItems.map((it, idx) => (
              <div key={idx} className="grid grid-cols-5 gap-2 items-center">
                <input
                  value={it.label}
                  onChange={(e)=>{
                    const v = e.target.value;
                    setRubricItems((prev)=> prev.map((p,i)=> i===idx? { ...p, label: v }: p));
                  }}
                  placeholder="Kriter"
                  className="col-span-3 px-3 py-2 border border-gray-300 rounded-md"
                />
                <input
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={it.weight}
                  onChange={(e)=>{
                    const v = parseFloat(e.target.value);
                    setRubricItems((prev)=> prev.map((p,i)=> i===idx? { ...p, weight: isNaN(v)? 0: v }: p));
                  }}
                  placeholder="Ağırlık (0-1)"
                  className="col-span-1 px-3 py-2 border border-gray-300 rounded-md"
                />
                <div className="col-span-1 flex justify-end gap-2">
                  <button
                    type="button"
                    className="text-sm px-2 py-1 border rounded"
                    onClick={()=> setRubricItems(prev=> prev.filter((_,i)=> i!==idx))}
                    aria-label="Kriteri kaldır"
                  >Sil</button>
                </div>
              </div>
            ))}
            <div className="flex justify-between mt-2">
              <button
                type="button"
                className="text-sm px-3 py-1 border rounded"
                onClick={()=> setRubricItems(prev=> [...prev, { label: "Yeni Kriter", weight: 0 }])}
              >Kriter Ekle</button>
              <button
                type="button"
                className="text-sm px-3 py-1 border rounded"
                onClick={()=>{
                  const t = title.toLowerCase();
                  let preset = [
                    { label: "Problem Çözme", weight: 0.25 },
                    { label: "Teknik Yeterlilik", weight: 0.45 },
                    { label: "İletişim", weight: 0.15 },
                    { label: "Kültür/İş Uygunluğu", weight: 0.15 },
                  ];
                  if (/(product|ürün|pm)/.test(t)) preset = [
                    { label: "Problem Çözme", weight: 0.25 },
                    { label: "Teknik/Alan", weight: 0.25 },
                    { label: "İletişim", weight: 0.25 },
                    { label: "Kültür/Uyum", weight: 0.25 },
                  ];
                  if (/(sales|satış|bdm|business development)/.test(t)) preset = [
                    { label: "İletişim/İkna", weight: 0.35 },
                    { label: "Teknik/Ürün Bilgisi", weight: 0.2 },
                    { label: "Problem Çözme", weight: 0.15 },
                    { label: "Kültür/Uyum", weight: 0.3 },
                  ];
                  if (/(marketing|pazarlama|growth)/.test(t)) preset = [
                    { label: "İletişim/Anlatı", weight: 0.35 },
                    { label: "Teknik/Analitik", weight: 0.25 },
                    { label: "Problem Çözme", weight: 0.2 },
                    { label: "Kültür/Uyum", weight: 0.2 },
                  ];
                  if (/(support|destek|müşteri)/.test(t)) preset = [
                    { label: "İletişim/Empati", weight: 0.4 },
                    { label: "Teknik/Ürün", weight: 0.2 },
                    { label: "Problem Çözme", weight: 0.15 },
                    { label: "Kültür/Uyum", weight: 0.25 },
                  ];
                  setRubricItems(preset);
                }}
              >Başlığa göre öner</button>
            </div>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Bağlantı süresi (gün)</label>
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
          <Button onClick={submit} aria-label="İlanı kaydet" disabled={extracting}>
            {extracting ? "Kaydediliyor ve AI çıkarılıyor…" : "İlanı Kaydet"}
          </Button>
        </div>
        {autoReqJson && (
          <div className="mt-4">
            <Label className="block text-sm font-medium text-gray-700 mb-1">Çıkarılan gereksinimler (önizleme)</Label>
            <pre className="text-xs bg-gray-50 border border-gray-200 rounded p-3 overflow-auto max-h-64">{autoReqJson}</pre>
          </div>
        )}
      </div>
    </div>
  );
} 
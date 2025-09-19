"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button, Label } from "@/components/ui";
import { apiFetch } from "@/lib/api";

export default function JobEditorPage(){
  const params = useParams();
  const jobId = Number(params?.id);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [rubricItems, setRubricItems] = useState<Array<{ label: string; weight: number }>>([]);
  const [rubricInfo, setRubricInfo] = useState<Array<{ label: string; weight: number }>>([]);

  useEffect(()=>{
    let mounted = true;
    (async ()=>{
      try {
        const job = await apiFetch<any>(`/api/v1/jobs/`);
        // API returns list; pick by id from context if needed
        // Fallback: fetch all and filter (no single GET endpoint here)
        const found = Array.isArray(job) ? job.find((j:any)=> j.id === jobId) : null;
        if (found){
          setTitle(found.title || "");
          setDescription(found.description || "");
          try {
            const r = found.rubric_json ? JSON.parse(found.rubric_json) : null;
            const arr = Array.isArray(r?.criteria) ? r.criteria : [];
            setRubricItems(arr.map((c:any)=> ({ label: String(c.label||""), weight: Number(c.weight)||0 })));
          } catch { setRubricItems([]); }
        }
        try{
          const rub = await apiFetch<any>(`/api/v1/metrics/rubric/${jobId}`);
          if (Array.isArray(rub?.criteria)) setRubricInfo(rub.criteria);
        }catch{}
      } catch (e:any) {
        setError(e.message || "Load failed");
      } finally {
        setLoading(false);
      }
    })();
    return ()=>{ mounted = false; };
  }, [jobId]);

  if (loading) return <div className="p-6">Yükleniyor…</div>;
  const total = rubricItems.reduce((s, it)=> s + (Number(it.weight)||0), 0);
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold">İlan Rubriği</h1>
      {error && <div className="text-red-600 text-sm">{error}</div>}
      <div className="space-y-4 bg-white border border-gray-200 rounded-lg p-4">
        <div>
          <Label className="block text-sm font-medium text-gray-700 mb-1">Başlık</Label>
          <input value={title} onChange={(e)=> setTitle(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-md" />
        </div>
        <div>
          <Label className="block text-sm font-medium text-gray-700 mb-1">Açıklama</Label>
          <textarea value={description} onChange={(e)=> setDescription(e.target.value)} rows={6} className="w-full px-3 py-2 border border-gray-300 rounded-md" />
        </div>
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label className="block text-sm font-medium text-gray-700">Rubrik (toplam=1.0)</Label>
            <span className="text-xs text-gray-500">Toplam: {total.toFixed(2)}</span>
          </div>
          {rubricInfo.length > 0 && (
            <div className="text-xs text-gray-500 mb-2">Mevcut ağırlıklar: {rubricInfo.map(r=> `${r.label}: ${Number(r.weight).toFixed(2)}`).join(" · ")}</div>
          )}
          <div className="space-y-2">
            {rubricItems.map((it, idx)=> (
              <div key={idx} className="grid grid-cols-5 gap-2 items-center">
                <input value={it.label} onChange={(e)=> setRubricItems(prev=> prev.map((p,i)=> i===idx? { ...p, label: e.target.value}: p))} className="col-span-3 px-3 py-2 border border-gray-300 rounded-md" />
                <input type="number" step="0.01" min={0} max={1} value={it.weight} onChange={(e)=>{
                  const v = parseFloat(e.target.value);
                  setRubricItems(prev=> prev.map((p,i)=> i===idx? { ...p, weight: isNaN(v)? 0 : v}: p));
                }} className="col-span-1 px-3 py-2 border border-gray-300 rounded-md" />
                <div className="col-span-1 flex justify-end">
                  <button type="button" onClick={()=> setRubricItems(prev=> prev.filter((_,i)=> i!==idx))} className="text-sm px-2 py-1 border rounded">Sil</button>
                </div>
              </div>
            ))}
            <div className="flex justify-between mt-2">
              <button type="button" className="text-sm px-3 py-1 border rounded" onClick={()=> setRubricItems(prev=> [...prev, { label: "Yeni Kriter", weight: 0 }])}>Kriter Ekle</button>
              <button type="button" className="text-sm px-3 py-1 border rounded" onClick={()=>{
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
                setRubricItems(preset);
              }}>Başlığa göre öner</button>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={()=> (window.location.href = "/jobs")}>Geri Dön</Button>
          <Button onClick={async ()=>{
            if (Math.abs(total - 1.0) > 0.01){ alert("Rubrik toplamı 1.0 olmalı"); return; }
            try{
              const rubric_json = JSON.stringify({ criteria: rubricItems });
              await apiFetch(`/api/v1/jobs/${jobId}`, { method: 'PUT', body: JSON.stringify({ title, description, rubric_json }) });
              window.location.href = "/jobs";
            }catch(e:any){ setError(e.message || 'Kaydetme hatası'); }
          }}>Kaydet</Button>
        </div>
      </div>
    </div>
  );
}



"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui";

export default function JobEditorPage(){
  const params = useParams();
  const jobId = Number(params?.id);
  // Removed manual requirements/rubric editing UI

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(()=>{
    let mounted = true;
    (async ()=>{
      try {
        // Nothing to load for editor anymore
      } catch (e:any) {
        setError(e.message || "Load failed");
      } finally {
        setLoading(false);
      }
    })();
    return ()=>{ mounted = false; };
  }, [jobId]);

  // Editor is deprecated; keep page for backward links with info

  if (loading) return <div className="p-6">Yükleniyor…</div>;
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold">Yapılandırma Kaldırıldı</h1>
      {error && <div className="text-red-600 text-sm">{error}</div>}
      <p className="text-gray-700">Bu sayfadaki &quot;gereksinim&quot; ve &quot;rubrik&quot; ayarları kaldırıldı. Sistem, iş ilanı metnine ve adayın özgeçmişine göre soruları otomatik uyarlar.</p>
      <div>
        <Button onClick={()=> (window.location.href = "/jobs")}>Geri Dön</Button>
      </div>
    </div>
  );
}



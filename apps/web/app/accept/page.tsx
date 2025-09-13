"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function PublicAcceptPage() {
  const [interviewId, setInterviewId] = useState<number | null>(null);
  const [slots, setSlots] = useState<{ start: string; end: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = Number(params.get("interview_id") || "0");
    setInterviewId(isFinite(id) && id > 0 ? id : null);
  }, []);

  useEffect(() => {
    const load = async () => {
      if (!interviewId) return;
      setLoading(true);
      setError(null);
      try {
        const res = await apiFetch<any>(`/api/v1/conversations/final-interview/proposals?interview_id=${interviewId}`, { skipRedirectOn401: true });
        const props = Array.isArray(res?.proposals) ? res.proposals : [];
        setSlots(props);
      } catch (e: any) {
        setError(e?.message || "Kayıt bulunamadı");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [interviewId]);

  const accept = async (idx: number) => {
    if (!interviewId) return;
    try {
      const res = await apiFetch(`/api/v1/conversations/final-interview/accept?interview_id=${interviewId}&slot=${idx}`, { method: "GET", skipRedirectOn401: true });
      setOk("Seçiminiz kaydedildi. Onay e-postası gönderildi.");
    } catch (e: any) {
      setError(e?.message || "Onay başarısız");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="max-w-xl w-full bg-white rounded-lg shadow p-6 border border-gray-200">
        <h1 className="text-xl font-semibold mb-4">Final Görüşme Zaman Seçimi</h1>
        {loading && <div className="text-sm text-gray-500">Yükleniyor…</div>}
        {error && <div className="text-sm text-rose-600 mb-2">{error}</div>}
        {ok && <div className="text-sm text-emerald-700 mb-2">{ok}</div>}
        {!loading && !error && slots.length === 0 && (
          <div className="text-sm text-gray-600">Uygun zaman aralığı bulunamadı. Lütfen insan kaynaklarıyla iletişime geçin.</div>
        )}
        <div className="space-y-3">
          {slots.map((s, i) => (
            <div key={i} className="flex items-center justify-between p-3 rounded border bg-gray-50">
              <div>
                <div className="font-medium text-gray-900">{new Date(s.start).toLocaleString("tr-TR")}</div>
                <div className="text-xs text-gray-600">— {new Date(s.end).toLocaleString("tr-TR")}</div>
              </div>
              <button className="px-3 py-1.5 text-sm rounded bg-brand-600 text-white hover:bg-brand-700" onClick={() => accept(i)}>
                Seç
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}



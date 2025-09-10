"use client";
import { useEffect, useMemo, useState } from "react";
import { MarketingNav } from "@/components/marketing/Nav";
import { MarketingFooter } from "@/components/marketing/Footer";
import { Button } from "@/components/ui";

export default function RoiPage() {
  const [candidateCount, setCandidateCount] = useState<number>(100);
  const [ikHourly, setIkHourly] = useState<number>(200);
  const [interviewerHourly, setInterviewerHourly] = useState<number>(300);
  const [avgMinutesPerCandidate, setAvgMinutesPerCandidate] = useState<number>(45);
  const [coordinationCost, setCoordinationCost] = useState<number>(5000);
  const [lateHireCost, setLateHireCost] = useState<number>(15000);
  const [platformMonthly, setPlatformMonthly] = useState<number>(5000);
  const [automationRate, setAutomationRate] = useState<number>(0.7); // 70%

  const traditional = useMemo(() => {
    const totalHours = (candidateCount * (avgMinutesPerCandidate / 60));
    const blendedHourly = (ikHourly + interviewerHourly) / 2;
    const processCost = totalHours * blendedHourly;
    return Math.round(processCost + coordinationCost + lateHireCost);
  }, [candidateCount, avgMinutesPerCandidate, ikHourly, interviewerHourly, coordinationCost, lateHireCost]);

  const withRecruiterAI = useMemo(() => {
    const reviewHours = (candidateCount * (avgMinutesPerCandidate / 60)) * (1 - automationRate) * 0.25; // only shortlist reviewed
    const reviewCost = reviewHours * ikHourly;
    return Math.round(platformMonthly + reviewCost);
  }, [candidateCount, avgMinutesPerCandidate, automationRate, platformMonthly, ikHourly]);

  const savings = Math.max(0, traditional - withRecruiterAI);
  const timeSavedHours = Math.max(0, (candidateCount * (avgMinutesPerCandidate / 60)) - ((candidateCount * (avgMinutesPerCandidate / 60)) * (1 - automationRate) * 0.25));

  const onPrint = () => {
    window.print();
  };

  useEffect(() => {
    // basic clamp
    setAutomationRate((r) => Math.min(0.95, Math.max(0, r)));
  }, [automationRate]);

  return (
    <div className="min-h-screen bg-white">
      <MarketingNav />
      <section className="px-6 py-12">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">ROI Hesaplayıcı</h1>
          <p className="text-gray-600 mb-8">Aday sayısı, süre ve maliyet varsayımlarınıza göre RecruiterAI ile elde edeceğiniz tasarrufu hesaplayın.</p>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="space-y-5">
              <NumberField label="Aday Sayısı" value={candidateCount} onChange={setCandidateCount} min={1} step={5} />
              <NumberField label="İK Saat Ücreti (₺)" value={ikHourly} onChange={setIkHourly} min={0} step={50} />
              <NumberField label="Mülakatçı Saat Ücreti (₺)" value={interviewerHourly} onChange={setInterviewerHourly} min={0} step={50} />
              <NumberField label="Aday Başına Süre (dk)" value={avgMinutesPerCandidate} onChange={setAvgMinutesPerCandidate} min={5} max={120} step={5} />
              <NumberField label="Koordinasyon Maliyeti (₺)" value={coordinationCost} onChange={setCoordinationCost} min={0} step={500} />
              <NumberField label="Geç İşe Alım Maliyeti (₺)" value={lateHireCost} onChange={setLateHireCost} min={0} step={1000} />
              <NumberField label="Platform Aylık (₺)" value={platformMonthly} onChange={setPlatformMonthly} min={0} step={500} />
              <PercentField label="Otomasyon Oranı (%)" value={automationRate} onChange={setAutomationRate} />
            </div>

            <div className="space-y-5">
              <div className="p-6 border rounded-lg">
                <h3 className="text-lg font-semibold mb-2">Geleneksel Süreç</h3>
                <p className="text-3xl font-bold text-gray-900">₺{traditional.toLocaleString("tr-TR")}</p>
              </div>
              <div className="p-6 border rounded-lg">
                <h3 className="text-lg font-semibold mb-2">RecruiterAI ile</h3>
                <p className="text-3xl font-bold text-green-700">₺{withRecruiterAI.toLocaleString("tr-TR")}</p>
              </div>
              <div className="p-6 border rounded-lg bg-green-50 border-green-200">
                <h3 className="text-lg font-semibold mb-2">Tasarruf</h3>
                <p className="text-3xl font-bold text-green-800">₺{savings.toLocaleString("tr-TR")}</p>
                <p className="text-sm text-green-900 mt-1">Zaman: ~{Math.round(timeSavedHours)} saat</p>
              </div>
              <div className="flex gap-3">
                <a href="/contact?utm_source=site&utm_medium=cta&utm_campaign=roi" className="inline-block">
                  <Button>Demo Talep Et</Button>
                </a>
                <Button variant="outline" onClick={onPrint}>PDF Olarak Kaydet</Button>
              </div>
            </div>
          </div>
        </div>
      </section>
      <MarketingFooter />
    </div>
  );
}

function NumberField({ label, value, onChange, min, max, step = 1 }: { label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type="number"
        className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-600"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

function PercentField({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  const pct = Math.round(value * 100);
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type="range"
        min={0}
        max={95}
        value={pct}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
        className="w-full"
      />
      <div className="text-xs text-gray-600 mt-1">{pct}%</div>
    </div>
  );
}



"use client";

import React, { useState, useEffect, useMemo } from "react";
import dynamic from "next/dynamic";
import { useDashboard } from "@/context/DashboardContext";
import { useDashboardStore, shallowCompare } from "@/lib/hooks/useDashboardStore";
import { AdvancedKPICard, KPIGrid, KPIData } from '@/components/analytics/AdvancedKPICard';
import { RealTimeAnalytics } from '@/components/analytics/RealTimeAnalytics';
import { ExportSystem, QuickExportButtons } from '@/components/analytics/ExportSystem';
import { ResponsiveGrid, MobileChartContainer, MobileDashboard, EnhancedCard, EnhancedCardContent, EnhancedCardHeader, EnhancedCardTitle, EnhancedButton } from '@/components/ui';
import { ThemeToggle } from '@/components/theme/ThemeToggle';
// Büyük grafik kütüphanesini başlangıç paketinden ayırmak için dinamik yükleme
const TrendChart = dynamic(() => import("@/components/ui/utils/Charts").then(m => m.TrendChart), { ssr: false });
const DonutChart = dynamic(() => import("@/components/ui/utils/Charts").then(m => m.DonutChart), { ssr: false });
import { apiFetch } from "@/lib/api";
import { Users, TimerReset, CheckCircle2, Briefcase, MessageSquare, TrendingUp, Target, Award, Clock } from "lucide-react";

export default function DashboardPage() {
  const { refreshData } = useDashboard();
  // Store selectorlar: sadece kullanılan dilimlere abone olur, shallow ile re-render azaltılır
  const candidates = useDashboardStore(s => s.candidates, shallowCompare);
  const jobs = useDashboardStore(s => s.jobs, shallowCompare);
  const interviews = useDashboardStore(s => s.interviews, shallowCompare);
  const loading = useDashboardStore(s => s.loading);
  
  // State for enhanced features
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isLive, setIsLive] = useState(true);
  const [weekly, setWeekly] = useState<any>(null);
  const [leaders, setLeaders] = useState<any>({});
  const [selectedPeriod, setSelectedPeriod] = useState<'7d' | '30d' | '90d'>('30d');
  const [calibration, setCalibration] = useState<any>(null);

  // Real metrics - only the essentials
  const enhancedMetrics = useMemo((): KPIData[] => {
    const completedInterviews = interviews.filter(i => i.status === "completed");
    
    return [
      {
        title: "Toplam Mülakatlar",
        value: interviews.length,
        // Don't show change percentages for empty data
        period: "Bu ay",
        unit: "adet",
        format: "number",
        status: interviews.length > 0 ? 'good' : 'warning',
      },
      {
        title: "Tamamlanan",
        value: completedInterviews.length,
        period: "Bu ay",
        unit: "adet", 
        format: "number",
        status: completedInterviews.length > 0 ? 'excellent' : 'warning',
      },
      {
        title: "Aktif Adaylar",
        value: candidates.length,
        period: "Toplam",
        unit: "kişi",
        format: "number",
        status: candidates.length > 0 ? 'good' : 'warning',
      },
      {
        title: "Açık Pozisyonlar",
        value: jobs.length,
        period: "Aktif",
        unit: "pozisyon",
        format: "number",
        status: jobs.length > 0 ? 'good' : 'warning',
      },
    ];
  }, [interviews, candidates, jobs]);

  // Real data for charts
  const chartData = useMemo(() => {
    const completedInterviews = interviews.filter(i => i.status === "completed");
    const pendingInterviews = interviews.filter(i => i.status === "pending");
    const inProgressInterviews = interviews.filter(i => i.status === "in_progress");
    
    return {
      trend: {
        labels: ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'],
        datasets: [
          {
            label: 'Mülakatlar',
            data: [0, 0, 0, 0, 0, 0, interviews.length], // Real data - most recent at end
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
          },
          {
            label: 'Tamamlanan',
            data: [0, 0, 0, 0, 0, 0, completedInterviews.length],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
          },
        ],
      },
      donut: {
        labels: ['Tamamlandı', 'Beklemede', 'Devam Ediyor', 'İptal'],
        datasets: [{
          data: [
            completedInterviews.length,
            pendingInterviews.length, 
            inProgressInterviews.length,
            0 // No cancelled interviews in current data
          ],
          backgroundColor: ['#10b981', '#f59e0b', '#3b82f6', '#ef4444'],
        }],
      },
    };
  }, [interviews]);

  // Data loading effect (calibration kaldırıldı)
  useEffect(() => {
    const loadData = async () => {
      try {
        await new Promise(resolve => setTimeout(resolve, 800));
        setLastUpdate(new Date());
      } catch (error) {
        console.error('Error loading data:', error);
      }
    };
    loadData();
    if (isLive) {
      const interval = setInterval(loadData, 5 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [isLive]);

  const headerContent = (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          📊 Dashboard
        </h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm">
          Temel metrikler ve özet bilgiler
        </p>
      </div>
      <div className="flex items-center space-x-3">
        <ThemeToggle />
        <button className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
          Dışa Aktar
        </button>
      </div>
    </div>
  );

  if (loading) {
    return (
      <MobileDashboard
        header={headerContent}
        className="animate-pulse"
      >
        <KPIGrid
          kpis={[]}
          columns={4}
          size="md"
          loading={true}
        />
      </MobileDashboard>
    );
  }

  return (
    <MobileDashboard
      header={headerContent}
    >
      <div className="space-y-8">
        {/* KPI Cards Grid */}
        <section>
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Temel Metrikler
            </h2>
            <div className="flex items-center space-x-4">
              <select
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value as any)}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
              >
                <option value="7d">Son 7 gün</option>
                <option value="30d">Son 30 gün</option>
                <option value="90d">Son 90 gün</option>
              </select>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Son güncelleme: {lastUpdate.toLocaleTimeString('tr-TR')}
              </span>
            </div>
          </div>
          
          <KPIGrid
            kpis={enhancedMetrics}
            columns={4}
            size="md"
            showTrend={false}
            showTarget={false}
          />
        </section>



        {/* Simple Charts - Only 2 most important */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Grafik Özeti
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <EnhancedCard>
              <EnhancedCardHeader>
                <EnhancedCardTitle className="text-base">Mülakat Durumları</EnhancedCardTitle>
              </EnhancedCardHeader>
              <EnhancedCardContent>
                <DonutChart data={chartData.donut} />
              </EnhancedCardContent>
            </EnhancedCard>

            <EnhancedCard>
              <EnhancedCardHeader>
                <EnhancedCardTitle className="text-base">Haftalık Trend</EnhancedCardTitle>
              </EnhancedCardHeader>
              <EnhancedCardContent>
                <TrendChart data={chartData.trend} />
              </EnhancedCardContent>
            </EnhancedCard>
          </div>
        </section>

        {/* Real Performance Summary */}
        <section>
          <EnhancedCard>
            <EnhancedCardHeader>
              <EnhancedCardTitle>
                📊 Performans Özeti
              </EnhancedCardTitle>
            </EnhancedCardHeader>
            <EnhancedCardContent className="text-center p-6">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {interviews.length > 0 ? Math.round((interviews.filter(i => i.status === "completed").length / interviews.length) * 100) : 0}%
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Tamamlanma</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {(() => {
                      // Ortalama süreyi sadece tek medya kaydı varsa (video ya da audio) veya her ikisi de varsa
                      // created_at -> completed_at farkından hesapla; böylece audio+video *çift sayılmaz*.
                      const completed = interviews.filter(i => i.status === "completed");
                      if (!completed.length) return "--";
                      const minutes = completed.map(it => {
                        if (it.completed_at && it.created_at) {
                          const ms = new Date(it.completed_at).getTime() - new Date(it.created_at).getTime();
                          return Math.max(0, ms / 60000);
                        }
                        return 0;
                      });
                      const avg = Math.round(minutes.reduce((a,b)=>a+b,0) / Math.max(1, minutes.length));
                      return `${avg}`;
                    })()}dk
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Ortalama Süre</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                    {(() => {
                      const scores = interviews
                        .map((i: any) => (typeof (i as any).overall_score === 'number' ? Number((i as any).overall_score) : null))
                        .filter((v: any) => typeof v === 'number') as number[];
                      if (!scores.length) return "--";
                      const avg100 = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
                      const avg5 = Math.round((avg100 / 20) * 10) / 10; // one decimal
                      return `${avg5}`;
                    })()}/5
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Ortalama Puan</div>
                </div>
              </div>
            </EnhancedCardContent>
          </EnhancedCard>
        </section>

        {/* Calibration card removed as per request */}
      </div>
    </MobileDashboard>
  );
}

"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useDashboard } from "@/context/DashboardContext";
import { AdvancedKPICard, KPIGrid, KPIData } from '@/components/analytics/AdvancedKPICard';
import { RealTimeAnalytics } from '@/components/analytics/RealTimeAnalytics';
import { ExportSystem, QuickExportButtons } from '@/components/analytics/ExportSystem';
import { ResponsiveGrid, MobileChartContainer, MobileDashboard, EnhancedCard, EnhancedCardContent, EnhancedCardHeader, EnhancedCardTitle, EnhancedButton } from '@/components/ui';
import { ThemeToggle } from '@/components/theme/ThemeToggle';
import { TrendChart, BarChart, ConversionFunnel, DonutChart, MetricCard, Heatmap } from "@/components/ui/utils/Charts";
import { apiFetch } from "@/lib/api";
import { Users, TimerReset, CheckCircle2, Briefcase, MessageSquare, TrendingUp, Target, Award, Clock } from "lucide-react";

export default function DashboardPage() {
  const { candidates, jobs, interviews, loading, refreshData } = useDashboard();
  
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

  // Data loading effect
  useEffect(() => {
    const loadData = async () => {
      try {
        // Simulate API calls
        await new Promise(resolve => setTimeout(resolve, 1000));
        setLastUpdate(new Date());
        try {
          const c = await apiFetch<any>(`/api/v1/conversations/analysis/calibration/summary`);
          setCalibration(c);
        } catch {}
      } catch (error) {
        console.error('Error loading data:', error);
      }
    };

    loadData();
    
    // Auto-refresh every 5 minutes if live
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
                    {interviews.length > 0 ? "--" : "0"}dk
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Ortalama Süre</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                    {interviews.length > 0 ? "--" : "0"}/5
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Ortalama Puan</div>
                </div>
              </div>
            </EnhancedCardContent>
          </EnhancedCard>
        </section>

        {/* Calibration Summary */}
        <section>
          <EnhancedCard>
            <EnhancedCardHeader>
              <EnhancedCardTitle>Kalibrasyon Özeti (AI Skoru vs Outcome)</EnhancedCardTitle>
            </EnhancedCardHeader>
            <EnhancedCardContent>
              {!calibration ? (
                <div className="text-sm text-gray-500">Veriler yükleniyor…</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <div className="text-2xl font-bold">{calibration.auc ?? '--'}</div>
                    <div className="text-sm text-gray-600">AUC</div>
                    <div className="text-xs text-gray-500 mt-1">Labeled: {calibration.labeled_count} / {calibration.count}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium">Pozitif Histogram</div>
                    <div className="flex gap-1 items-end h-16 mt-1">
                      {(calibration.hist?.pos || []).map((v:number,i:number)=> (
                        <div key={i} style={{ height: `${(v||0)*6}px` }} className="w-2 bg-emerald-500" />
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-medium">Negatif Histogram</div>
                    <div className="flex gap-1 items-end h-16 mt-1">
                      {(calibration.hist?.neg || []).map((v:number,i:number)=> (
                        <div key={i} style={{ height: `${(v||0)*6}px` }} className="w-2 bg-rose-500" />
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </EnhancedCardContent>
          </EnhancedCard>
        </section>
      </div>
    </MobileDashboard>
  );
}

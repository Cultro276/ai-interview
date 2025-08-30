"use client";
import { useDashboard } from "@/context/DashboardContext";
import { useEffect, useState, useMemo } from "react";
import { Button } from "@/components/ui";
import { Card, CardContent, CardHeader } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { Users, TimerReset, CheckCircle2, Briefcase, MessageSquare, TrendingUp, Target, Award, Clock } from "lucide-react";
import { TrendChart, BarChart, ConversionFunnel, DonutChart, MetricCard, Heatmap } from "@/components/ui";

type Weekly = { interviews_created_7d:number; interviews_completed_7d:number };
type Leader = { interview_id:number; candidate_id:number; candidate_name:string|null; overall_score:number|null };
// Removed requirements coverage types; endpoint deprecated

export default function DashboardPageClassic() {
  const { candidates, jobs, interviews, loading, refreshData } = useDashboard();

  const [weekly, setWeekly] = useState<Weekly | null>(null);
  const [leaders, setLeaders] = useState<Record<number, Leader[]>>({});
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isLive, setIsLive] = useState(true);
  // Removed requirements coverage state; endpoint deprecated

  // Calculate advanced metrics
  const metrics = useMemo(() => {
    const completedInterviews = interviews.filter(i => i.status === "completed");
    const pendingInterviews = interviews.filter(i => i.status === "pending");
    
    const completionRate = interviews.length > 0 ? Math.round((completedInterviews.length / interviews.length) * 100) : 0;
    const avgDuration = completedInterviews.length > 0 ? 
      Math.round(completedInterviews.reduce((acc, i) => {
        if (i.completed_at && i.created_at) {
          const duration = new Date(i.completed_at).getTime() - new Date(i.created_at).getTime();
          return acc + (duration / (1000 * 60)); // minutes
        }
        return acc;
      }, 0) / completedInterviews.length) : 0;

    // Conversion funnel data
    const funnelSteps = [
      { name: "Toplam Aday", count: candidates.length, percentage: 100, color: "#3B82F6" },
      { name: "Mülakat Başlatılan", count: interviews.length, percentage: interviews.length > 0 ? Math.round((interviews.length / candidates.length) * 100) : 0, color: "#8B5CF6" },
      { name: "Tamamlanan", count: completedInterviews.length, percentage: candidates.length > 0 ? Math.round((completedInterviews.length / candidates.length) * 100) : 0, color: "#10B981" },
      { name: "Başarılı", count: Math.round(completedInterviews.length * 0.3), percentage: candidates.length > 0 ? Math.round((completedInterviews.length * 0.3 / candidates.length) * 100) : 0, color: "#F59E0B" }
    ];

    return {
      completionRate,
      avgDuration,
      funnelSteps,
      successRate: completedInterviews.length > 0 ? Math.round((completedInterviews.length * 0.3 / completedInterviews.length) * 100) : 0,
      pendingCount: pendingInterviews.length
    };
  }, [candidates, interviews]);

  // Auto-refresh effect
  useEffect(() => {
    const loadData = async () => {
      try { 
        const w = await apiFetch<Weekly>("/api/v1/metrics/weekly"); 
        setWeekly(w); 
      } catch {}
      
      // Preload leaderboards for latest up to 3 jobs
      try {
        const topJobs = jobs.slice(0, 3);
        const entries = await Promise.all(topJobs.map(j => apiFetch<Leader[]>(`/api/v1/jobs/${j.id}/leaderboard`)));
        const mapped: Record<number, Leader[]> = {};
        topJobs.forEach((j, idx) => { mapped[j.id] = entries[idx] || []; });
        setLeaders(mapped);
      } catch {}
      
      setLastUpdate(new Date());
    };

    loadData();

    // Auto-refresh every 5 minutes if live
    const interval = isLive ? setInterval(() => {
      refreshData();
      loadData();
    }, 5 * 60 * 1000) : null;

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [jobs.length, interviews.length, isLive, refreshData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-300">Panel yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-neutral-100">Panel (Klasik)</h1>
          <div className="flex items-center gap-3 mt-2">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}></div>
              <span>{isLive ? 'Canlı' : 'Durduruldu'}</span>
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Son güncelleme: {lastUpdate.toLocaleTimeString('tr-TR')}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => setIsLive(!isLive)}
          >
            {isLive ? 'Durdur' : 'Başlat'}
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              // Simple export to JSON for now
              const data = {
                metrics,
                candidates: candidates.length,
                interviews: interviews.length,
                jobs: jobs.length,
                lastUpdate
              };
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `dashboard-${new Date().toISOString().split('T')[0]}.json`;
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            📥 Dışa Aktar
          </Button>
          <Button onClick={refreshData}>Yenile</Button>
        </div>
      </div>

      {/* Enhanced KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="Toplam Aday"
          value={candidates.length}
          icon={<Users className="w-6 h-6" />}
          color="blue"
        />
        
        <MetricCard
          title="Tamamlanma Oranı"
          value={`%${metrics.completionRate}`}
          trend={metrics.completionRate > 70 ? 'up' : metrics.completionRate > 40 ? 'neutral' : 'down'}
          icon={<Target className="w-6 h-6" />}
          color="green"
        />

        <MetricCard
          title="Ortalama Süre"
          value={`${metrics.avgDuration} dk`}
          trend={metrics.avgDuration < 30 ? 'up' : 'neutral'}
          icon={<Clock className="w-6 h-6" />}
          color="yellow"
        />

        <MetricCard
          title="Başarı Oranı"
          value={`%${metrics.successRate}`}
          trend={metrics.successRate > 25 ? 'up' : 'down'}
          icon={<Award className="w-6 h-6" />}
          color="purple"
        />

        <MetricCard
          title="7 Gün Yeni"
          value={weekly?.interviews_created_7d ?? "—"}
          icon={<TrendingUp className="w-6 h-6" />}
          color="indigo"
        />

        <MetricCard
          title="Bekleyen"
          value={metrics.pendingCount}
          trend={metrics.pendingCount > 5 ? 'down' : 'up'}
          icon={<TimerReset className="w-6 h-6" />}
          color="red"
        />

        <MetricCard
          title="Aktif İlan"
          value={jobs.length}
          icon={<Briefcase className="w-6 h-6" />}
          color="green"
        />

        <MetricCard
          title="Toplam Mülakat"
          value={interviews.length}
          icon={<MessageSquare className="w-6 h-6" />}
          color="blue"
        />
      </div>

      {/* Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Conversion Funnel */}
        <Card className="bg-white dark:bg-neutral-900 shadow border border-gray-200 dark:border-neutral-800">
          <CardHeader>
            <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100">Dönüşüm Analizi</h3>
          </CardHeader>
          <CardContent>
            <ConversionFunnel steps={metrics.funnelSteps} />
          </CardContent>
        </Card>

        {/* Status Distribution */}
        <Card className="bg-white dark:bg-neutral-900 shadow border border-gray-200 dark:border-neutral-800">
          <CardHeader>
            <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100">Mülakat Durumları</h3>
          </CardHeader>
          <CardContent>
            <DonutChart
              data={{
                labels: ['Tamamlanan', 'Bekleyen'],
                datasets: [{
                  data: [
                    interviews.filter(i => i.status === "completed").length,
                    interviews.filter(i => i.status === "pending").length
                  ],
                  backgroundColor: ['#10B981', '#F59E0B', '#EF4444'],
                  borderColor: ['#059669', '#D97706', '#DC2626']
                }]
              }}
            />
          </CardContent>
        </Card>
      </div>

      {/* Recent Interviews */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg shadow border border-gray-200 dark:border-neutral-800 mb-8">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-neutral-800">
          <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100">Son Görüşmeler</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-neutral-800">
            <thead className="bg-gray-50 dark:bg-neutral-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Aday</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">İlan</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Durum</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Tarih</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Kayıt</th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-neutral-900 divide-y divide-gray-200 dark:divide-neutral-800">
              {interviews.slice(0, 5).map((interview) => {
                const candidate = candidates.find(c => c.id === interview.candidate_id);
                const job = jobs.find(j => j.id === interview.job_id);
                return (
                  <tr key={interview.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-neutral-100">
                      {candidate?.name || "Unknown"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                      {job?.title || "Unknown"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        interview.status === "completed" 
                          ? "bg-green-100 text-green-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}>
                        {interview.status === "completed" ? "Tamamlandı" : interview.status === "pending" ? "Bekliyor" : interview.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                      {new Date(interview.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                      <div className="flex space-x-2">
                        {interview.audio_url && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Ses ✓
                          </span>
                        )}
                        {interview.video_url && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            Video ✓
                          </span>
                        )}
                        {!interview.audio_url && !interview.video_url && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            Kayıt yok
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trend Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Weekly Trend */}
        <Card className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800">
          <CardHeader>
            <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100">Haftalık Trend</h3>
          </CardHeader>
          <CardContent>
            <TrendChart
              data={{
                labels: ['6 hafta önce', '5 hafta önce', '4 hafta önce', '3 hafta önce', '2 hafta önce', 'Geçen hafta', 'Bu hafta'],
                datasets: [
                  {
                    label: 'Başlatılan',
                    data: [12, 19, 15, 22, 18, weekly?.interviews_created_7d || 0, Math.round((weekly?.interviews_created_7d || 0) * 1.1)],
                    borderColor: '#3B82F6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true
                  },
                  {
                    label: 'Tamamlanan',
                    data: [8, 14, 12, 18, 16, weekly?.interviews_completed_7d || 0, Math.round((weekly?.interviews_completed_7d || 0) * 1.2)],
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true
                  }
                ]
              }}
            />
          </CardContent>
        </Card>

        {/* Job Performance */}
        <Card className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800">
          <CardHeader>
            <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100">Pozisyon Performansı</h3>
          </CardHeader>
          <CardContent>
            <BarChart
              data={{
                labels: jobs.slice(0, 5).map(j => j.title.substring(0, 15) + (j.title.length > 15 ? '...' : '')),
                datasets: [
                  {
                    label: 'Başvuru',
                    data: jobs.slice(0, 5).map(() => Math.floor(Math.random() * 50) + 10),
                    backgroundColor: '#8B5CF6'
                  },
                  {
                    label: 'Tamamlanan',
                    data: jobs.slice(0, 5).map(() => Math.floor(Math.random() * 30) + 5),
                    backgroundColor: '#10B981'
                  }
                ]
              }}
            />
          </CardContent>
        </Card>
      </div>

      {/* Performance Heatmap */}
      <Card className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 mb-8">
        <CardHeader>
          <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100">Pozisyon Başarı Haritası</h3>
        </CardHeader>
        <CardContent>
          <Heatmap
            data={jobs.map(job => ({
              label: job.title.substring(0, 20) + (job.title.length > 20 ? '...' : ''),
              value: Math.floor(Math.random() * 100), // Mock data - in real app, calculate from actual success rates
              color: ''
            }))}
            title=""
            maxValue={100}
          />
        </CardContent>
      </Card>

      {/* Job leaderboards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {jobs.slice(0, 3).map(job => (
          <Card key={job.id} className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-300">İş</div>
                  <div className="text-base font-semibold text-gray-900 dark:text-neutral-100">{job.title}</div>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">Top 5</div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <ul className="divide-y divide-gray-200 dark:divide-neutral-800">
                {(leaders[job.id] || []).slice(0, 5).map((row) => (
                  <li key={row.interview_id} className="px-4 py-3 flex items-center justify-between text-sm">
                    <span className="truncate max-w-[70%] text-gray-900 dark:text-neutral-100">{row.candidate_name || `#${row.candidate_id}`}</span>
                    <span className="text-gray-700 dark:text-gray-300">{row.overall_score ?? "—"}</span>
                  </li>
                ))}
                {(!leaders[job.id] || leaders[job.id].length === 0) && (
                  <li className="px-4 py-6 text-sm text-gray-500 dark:text-gray-400">Veri yok</li>
                )}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
} 

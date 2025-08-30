"use client";
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import { Radar } from 'react-chartjs-2';

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

interface CompetencyScore {
  competency: string;
  score: number;
  benchmark?: number;
  level: "expert" | "proficient" | "basic" | "none";
}

interface CompetencyRadarProps {
  competencies: CompetencyScore[];
  title?: string;
  candidateName?: string;
  showBenchmark?: boolean;
}

export function CompetencyRadar({ 
  competencies, 
  title = "360° Yetkinlik Analizi", 
  candidateName = "Aday",
  showBenchmark = true 
}: CompetencyRadarProps) {
  
  const labels = competencies.map(c => c.competency);
  const candidateScores = competencies.map(c => c.score);
  const benchmarkScores = competencies.map(c => c.benchmark || 70);
  
  const data = {
    labels: labels,
    datasets: [
      {
        label: candidateName,
        data: candidateScores,
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.2)',
        borderWidth: 2,
        pointBackgroundColor: 'rgb(59, 130, 246)',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgb(59, 130, 246)',
      },
      ...(showBenchmark ? [{
        label: 'Pozisyon Benchmarkı',
        data: benchmarkScores,
        borderColor: 'rgb(156, 163, 175)',
        backgroundColor: 'rgba(156, 163, 175, 0.1)',
        borderWidth: 1,
        borderDash: [5, 5],
        pointBackgroundColor: 'rgb(156, 163, 175)',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgb(156, 163, 175)',
      }] : [])
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            const competency = competencies[context.dataIndex];
            const level = competency.level === "expert" ? "Uzman" :
                         competency.level === "proficient" ? "Yetkin" :
                         competency.level === "basic" ? "Temel" : "Yok";
            return `${context.dataset.label}: ${context.parsed.r}/100 (${level})`;
          }
        }
      }
    },
    scales: {
      r: {
        angleLines: {
          display: true
        },
        suggestedMin: 0,
        suggestedMax: 100,
        pointLabels: {
          font: {
            size: 12
          }
        },
        ticks: {
          stepSize: 20,
          font: {
            size: 10
          }
        }
      }
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case "expert": return "bg-purple-100 text-purple-800";
      case "proficient": return "bg-blue-100 text-blue-800";
      case "basic": return "bg-yellow-100 text-yellow-800";
      case "none": return "bg-gray-100 text-gray-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
        🎯 {title}
      </h3>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Radar Chart */}
        <div className="bg-white p-6 rounded-xl border border-gray-200">
          <div className="h-80 w-full">
            <Radar data={data} options={options} />
          </div>
        </div>

        {/* Competency Details */}
        <div className="space-y-4">
          <h4 className="font-semibold text-gray-800">Detaylı Yetkinlik Değerlendirmesi</h4>
          {competencies.map((comp, index) => (
            <div key={index} className="bg-gray-50 p-4 rounded-lg border">
              <div className="flex items-center justify-between mb-2">
                <h5 className="font-medium text-gray-900">{comp.competency}</h5>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-bold ${getScoreColor(comp.score)}`}>
                    {comp.score}/100
                  </span>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${getLevelColor(comp.level)}`}>
                    {comp.level === "expert" ? "Uzman" :
                     comp.level === "proficient" ? "Yetkin" :
                     comp.level === "basic" ? "Temel" : "Yok"}
                  </span>
                </div>
              </div>
              
              {/* Progress bar */}
              <div className="relative">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${
                      comp.score >= 80 ? 'bg-green-500' :
                      comp.score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${comp.score}%` }}
                  ></div>
                </div>
                {showBenchmark && comp.benchmark && (
                  <div 
                    className="absolute top-0 w-0.5 h-2 bg-gray-600"
                    style={{ left: `${comp.benchmark}%` }}
                    title={`Benchmark: ${comp.benchmark}`}
                  ></div>
                )}
              </div>
              
              {showBenchmark && comp.benchmark && (
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0</span>
                  <span className="text-gray-700">Benchmark: {comp.benchmark}</span>
                  <span>100</span>
                </div>
              )}
              
              {/* Performance indicator */}
              <div className="mt-2 text-xs">
                {comp.score > (comp.benchmark || 70) ? (
                  <span className="text-green-600 font-medium">✓ Benchmark'ın üstünde</span>
                ) : comp.score >= (comp.benchmark || 70) - 10 ? (
                  <span className="text-yellow-600 font-medium">~ Benchmark seviyesinde</span>
                ) : (
                  <span className="text-red-600 font-medium">⚠ Geliştirilmesi gereken alan</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-xl border border-blue-200">
        <h4 className="font-semibold text-gray-800 mb-4">📊 Özet İstatistikler</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {Math.round(competencies.reduce((acc, c) => acc + c.score, 0) / competencies.length)}
            </div>
            <div className="text-sm text-gray-600">Genel Ortalama</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {competencies.filter(c => c.score >= 80).length}
            </div>
            <div className="text-sm text-gray-600">Güçlü Alanlar</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {competencies.filter(c => c.score >= 60 && c.score < 80).length}
            </div>
            <div className="text-sm text-gray-600">Geliştirilecek</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">
              {competencies.filter(c => c.score < 60).length}
            </div>
            <div className="text-sm text-gray-600">Kritik Alanlar</div>
          </div>
        </div>
      </div>
    </div>
  );
}

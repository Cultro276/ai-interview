"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui";
// Progress component defined inline to avoid import issues
interface ProgressProps {
  value: number;
  className?: string;
}

function Progress({ value, className }: ProgressProps) {
  return (
    <div className={`relative h-2 w-full overflow-hidden rounded-full bg-gray-200 ${className || ''}`}>
      <div
        className="h-full bg-blue-600 transition-all"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

interface LiveInsightsProps {
  askedCount: number;
  elapsedMinutes: number;
  history: Array<{ role: string; text: string }>;
  isActive: boolean;
}

interface InsightScores {
  communication: number;
  confidence: number;
  technical_depth: number;
  response_quality: number;
  overall_progress: number;
}

export function LiveInsights({ askedCount, elapsedMinutes, history, isActive }: LiveInsightsProps) {
  const [scores, setScores] = useState<InsightScores>({
    communication: 0,
    confidence: 0,
    technical_depth: 0,
    response_quality: 0,
    overall_progress: 0
  });

  // Calculate live scores based on conversation patterns
  useEffect(() => {
    if (!isActive || history.length === 0) return;

    const userResponses = history.filter(h => h.role === "user");
    const avgResponseLength = userResponses.length > 0 
      ? userResponses.reduce((acc, r) => acc + r.text.length, 0) / userResponses.length 
      : 0;

    // Mock intelligent scoring - in real implementation, this would use NLP analysis
    const newScores: InsightScores = {
      communication: Math.min(100, Math.max(0, (avgResponseLength / 100) * 100)), // Based on response detail
      confidence: Math.min(100, Math.max(0, 70 + (userResponses.length * 5))), // Improves with responses
      technical_depth: Math.min(100, Math.max(0, 40 + (askedCount * 10))), // Grows with questions
      response_quality: Math.min(100, Math.max(0, 60 + Math.random() * 30)), // Simulated quality
      overall_progress: Math.min(100, (askedCount / 8) * 100) // Based on expected 8 questions
    };

    setScores(newScores);
  }, [history, askedCount, isActive]);

  if (!isActive) return null;

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    return "text-red-600";
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return "bg-green-500";
    if (score >= 60) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <Card className="fixed top-4 right-4 w-80 bg-white/95 backdrop-blur-sm shadow-lg border-2 border-blue-200 z-50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700">📊 Canlı Analiz</h3>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-xs text-gray-500">{elapsedMinutes} dk</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall Progress */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-gray-600">Mülakat İlerlemesi</span>
            <span className="font-medium">{Math.round(scores.overall_progress)}%</span>
          </div>
          <Progress value={scores.overall_progress} className="h-2" />
        </div>

        {/* Individual Scores */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-600">💬 İletişim</span>
            <div className="flex items-center gap-2">
              <div className={`w-16 h-1.5 rounded-full ${getProgressColor(scores.communication)}`} 
                   style={{ width: `${Math.max(8, scores.communication * 0.6)}px` }}></div>
              <span className={`text-xs font-medium ${getScoreColor(scores.communication)}`}>
                {Math.round(scores.communication)}
              </span>
            </div>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-600">🎯 Güven</span>
            <div className="flex items-center gap-2">
              <div className={`w-16 h-1.5 rounded-full ${getProgressColor(scores.confidence)}`} 
                   style={{ width: `${Math.max(8, scores.confidence * 0.6)}px` }}></div>
              <span className={`text-xs font-medium ${getScoreColor(scores.confidence)}`}>
                {Math.round(scores.confidence)}
              </span>
            </div>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-600">🔧 Teknik Derinlik</span>
            <div className="flex items-center gap-2">
              <div className={`w-16 h-1.5 rounded-full ${getProgressColor(scores.technical_depth)}`} 
                   style={{ width: `${Math.max(8, scores.technical_depth * 0.6)}px` }}></div>
              <span className={`text-xs font-medium ${getScoreColor(scores.technical_depth)}`}>
                {Math.round(scores.technical_depth)}
              </span>
            </div>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-600">⭐ Cevap Kalitesi</span>
            <div className="flex items-center gap-2">
              <div className={`w-16 h-1.5 rounded-full ${getProgressColor(scores.response_quality)}`} 
                   style={{ width: `${Math.max(8, scores.response_quality * 0.6)}px` }}></div>
              <span className={`text-xs font-medium ${getScoreColor(scores.response_quality)}`}>
                {Math.round(scores.response_quality)}
              </span>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="pt-2 border-t border-gray-200">
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="text-center">
              <div className="font-bold text-blue-600">{askedCount}</div>
              <div className="text-gray-500">Soru</div>
            </div>
            <div className="text-center">
              <div className="font-bold text-purple-600">{history.filter(h => h.role === "user").length}</div>
              <div className="text-gray-500">Cevap</div>
            </div>
          </div>
        </div>

        {/* Live Tips */}
        {scores.communication < 50 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
            <p className="text-xs text-yellow-700">
              💡 İpucu: Daha detaylı ve açıklayıcı cevaplar verin
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

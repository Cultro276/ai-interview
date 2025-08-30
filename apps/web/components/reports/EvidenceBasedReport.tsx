"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui";

interface EvidenceItem {
  claim: string;
  evidence_quotes: string[];
  confidence_level: number;
  verification_status: "verified" | "needs_verification" | "conflicting";
}

interface BehavioralPattern {
  pattern: string;
  frequency: number;
  examples: string[];
  impact: "positive" | "negative" | "neutral";
}

interface CompetencyEvidence {
  competency: string;
  level: "expert" | "proficient" | "basic" | "none";
  supporting_quotes: string[];
  behavioral_indicators: string[];
}

interface EvidenceBasedReportProps {
  evidence: EvidenceItem[];
  behavioral_patterns: BehavioralPattern[];
  competency_evidence: CompetencyEvidence[];
  transcript: string;
}

export function EvidenceBasedReport({ 
  evidence, 
  behavioral_patterns, 
  competency_evidence, 
  transcript 
}: EvidenceBasedReportProps) {
  const [selectedQuote, setSelectedQuote] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"evidence" | "patterns" | "competencies">("evidence");

  const getVerificationIcon = (status: string) => {
    switch (status) {
      case "verified": return "✅";
      case "needs_verification": return "❓";
      case "conflicting": return "⚠️";
      default: return "🔍";
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return "text-green-600 bg-green-50";
    if (confidence >= 60) return "text-yellow-600 bg-yellow-50";
    return "text-red-600 bg-red-50";
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

  const highlightQuoteInTranscript = (quote: string) => {
    if (!quote || !transcript) return transcript;
    
    const highlightedTranscript = transcript.replace(
      new RegExp(quote.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'),
      `<mark class="bg-yellow-200 px-1 rounded">${quote}</mark>`
    );
    
    return highlightedTranscript;
  };

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200">
        <button
          className={`px-4 py-2 font-medium text-sm ${
            activeTab === "evidence" 
              ? "border-b-2 border-blue-500 text-blue-600" 
              : "text-gray-500 hover:text-gray-700"
          }`}
          onClick={() => setActiveTab("evidence")}
        >
          🔍 Kanıt Analizi
        </button>
        <button
          className={`px-4 py-2 font-medium text-sm ${
            activeTab === "patterns" 
              ? "border-b-2 border-blue-500 text-blue-600" 
              : "text-gray-500 hover:text-gray-700"
          }`}
          onClick={() => setActiveTab("patterns")}
        >
          📊 Davranış Kalıpları
        </button>
        <button
          className={`px-4 py-2 font-medium text-sm ${
            activeTab === "competencies" 
              ? "border-b-2 border-blue-500 text-blue-600" 
              : "text-gray-500 hover:text-gray-700"
          }`}
          onClick={() => setActiveTab("competencies")}
        >
          ⭐ Yetkinlik Kanıtları
        </button>
      </div>

      {/* Evidence Analysis Tab */}
      {activeTab === "evidence" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">İddia ve Kanıtlar</h3>
            {evidence.map((item, index) => (
              <Card key={index} className="border-l-4 border-l-blue-500">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <h4 className="font-medium text-gray-900">{item.claim}</h4>
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{getVerificationIcon(item.verification_status)}</span>
                      <span className={`text-xs px-2 py-1 rounded-full ${getConfidenceColor(item.confidence_level)}`}>
                        %{item.confidence_level}
                      </span>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <span className="text-sm font-medium text-gray-700">Destekleyici Alıntılar:</span>
                    {item.evidence_quotes.map((quote, qIndex) => (
                      <div 
                        key={qIndex}
                        className="p-3 bg-gray-50 rounded border-l-3 border-l-gray-300 cursor-pointer hover:bg-gray-100"
                        onClick={() => setSelectedQuote(quote)}
                      >
                        <p className="text-sm text-gray-700 italic">"{quote}"</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Transcript with highlighting */}
          <div className="sticky top-4">
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold text-gray-900">Mülakat Transkripti</h3>
                {selectedQuote && (
                  <p className="text-sm text-blue-600">Seçili alıntı: "{selectedQuote.substring(0, 50)}..."</p>
                )}
              </CardHeader>
              <CardContent>
                <div 
                  className="max-h-96 overflow-y-auto text-sm text-gray-700 leading-relaxed"
                  dangerouslySetInnerHTML={{ 
                    __html: selectedQuote ? highlightQuoteInTranscript(selectedQuote) : transcript 
                  }}
                />
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Behavioral Patterns Tab */}
      {activeTab === "patterns" && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Tespit Edilen Davranış Kalıpları</h3>
          {behavioral_patterns.map((pattern, index) => (
            <Card key={index} className={`border-l-4 ${
              pattern.impact === "positive" ? "border-l-green-500" :
              pattern.impact === "negative" ? "border-l-red-500" : "border-l-yellow-500"
            }`}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <h4 className="font-medium text-gray-900">{pattern.pattern}</h4>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      pattern.impact === "positive" ? "bg-green-100 text-green-800" :
                      pattern.impact === "negative" ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800"
                    }`}>
                      {pattern.impact === "positive" ? "Olumlu" : 
                       pattern.impact === "negative" ? "Olumsuz" : "Nötr"}
                    </span>
                    <span className="text-xs text-gray-500">
                      {pattern.frequency} kez gözlemlendi
                    </span>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <span className="text-sm font-medium text-gray-700">Örnekler:</span>
                  {pattern.examples.map((example, eIndex) => (
                    <div key={eIndex} className="p-2 bg-gray-50 rounded text-sm text-gray-700">
                      "{example}"
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Competency Evidence Tab */}
      {activeTab === "competencies" && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Yetkinlik Değerlendirmeleri</h3>
          {competency_evidence.map((comp, index) => (
            <Card key={index}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <h4 className="font-medium text-gray-900">{comp.competency}</h4>
                  <span className={`text-xs px-3 py-1 rounded-full font-medium ${getLevelColor(comp.level)}`}>
                    {comp.level === "expert" ? "Uzman" :
                     comp.level === "proficient" ? "Yetkin" :
                     comp.level === "basic" ? "Temel" : "Yok"}
                  </span>
                </div>
                
                <div className="space-y-3">
                  <div>
                    <span className="text-sm font-medium text-gray-700">Destekleyici Alıntılar:</span>
                    {comp.supporting_quotes.map((quote, qIndex) => (
                      <div key={qIndex} className="mt-1 p-2 bg-blue-50 rounded text-sm text-blue-800">
                        "{quote}"
                      </div>
                    ))}
                  </div>
                  
                  <div>
                    <span className="text-sm font-medium text-gray-700">Davranışsal Göstergeler:</span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {comp.behavioral_indicators.map((indicator, iIndex) => (
                        <span key={iIndex} className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded">
                          {indicator}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

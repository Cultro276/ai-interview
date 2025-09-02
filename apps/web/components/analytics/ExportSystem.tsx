'use client';

import React, { useState } from 'react';
import { EnhancedButton, EnhancedCard } from '@/components/ui';
import { cn } from '@/components/ui/cn';
import { apiFetch } from '@/lib/api';

export type ExportFormat = 'pdf' | 'excel' | 'csv' | 'json';
export type ExportDataType = 'dashboard' | 'interviews' | 'candidates' | 'reports' | 'custom';

interface ExportOptions {
  format: ExportFormat;
  dataType: ExportDataType;
  dateRange?: {
    start: Date;
    end: Date;
  };
  filters?: Record<string, any>;
  includeCharts?: boolean;
  includeRawData?: boolean;
  fileName?: string;
}

interface ExportSystemProps {
  onExport?: (options: ExportOptions) => Promise<void>;
  availableDataTypes?: ExportDataType[];
  className?: string;
  interviewId?: number; // For interview-specific exports
  jobId?: number; // For bulk job exports
}

export function ExportSystem({
  onExport,
  availableDataTypes = ['dashboard', 'interviews', 'candidates', 'reports'],
  className,
  interviewId,
  jobId,
}: ExportSystemProps) {
  // const toastContext = useToast();
  // const addToast = toastContext?.addToast || (() => {});
  const addToast = (message: string, type: 'success' | 'error') => {
    console.log(`Toast ${type}: ${message}`);
  };
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('pdf');
  const [selectedDataType, setSelectedDataType] = useState<ExportDataType>('dashboard');
  const [includeCharts, setIncludeCharts] = useState(true);
  const [includeRawData, setIncludeRawData] = useState(false);
  const [fileName, setFileName] = useState('');
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
    end: new Date(),
  });

  const formatOptions = [
    {
      value: 'pdf' as ExportFormat,
      label: 'PDF Raporu',
      description: 'Yazdırılabilir rapor formatı',
      icon: '📄',
      color: 'text-red-600',
    },
    {
      value: 'excel' as ExportFormat,
      label: 'Excel Dosyası',
      description: 'Analiz için elektronik tablo',
      icon: '📊',
      color: 'text-green-600',
    },
    {
      value: 'csv' as ExportFormat,
      label: 'CSV Dosyası',
      description: 'Ham veri, virgülle ayrılmış',
      icon: '📈',
      color: 'text-blue-600',
    },
    {
      value: 'json' as ExportFormat,
      label: 'JSON Dosyası',
      description: 'API entegrasyonu için',
      icon: '🔧',
      color: 'text-purple-600',
    },
  ];

  const dataTypeOptions = [
    {
      value: 'dashboard' as ExportDataType,
      label: 'Dashboard Raporu',
      description: 'Genel dashboard metrikleri',
    },
    {
      value: 'interviews' as ExportDataType,
      label: 'Mülakat Verileri',
      description: 'Tüm mülakat detayları',
    },
    {
      value: 'candidates' as ExportDataType,
      label: 'Aday Bilgileri',
      description: 'Aday profilleri ve skorları',
    },
    {
      value: 'reports' as ExportDataType,
      label: 'Analiz Raporları',
      description: 'Detaylı analiz ve insights',
    },
  ];

  const handleExport = async () => {
    if (!onExport) return;

    setIsExporting(true);
    try {
      const options: ExportOptions = {
        format: selectedFormat,
        dataType: selectedDataType,
        dateRange,
        includeCharts: selectedFormat === 'pdf' ? includeCharts : false,
        includeRawData,
        fileName: fileName || `${selectedDataType}_${new Date().toISOString().split('T')[0]}`,
      };

      await onExport(options);
      setIsOpen(false);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  const formatDate = (date: Date) => {
    return date.toISOString().split('T')[0];
  };

  // Real API export functionality
  const handleRealExport = async (options: ExportOptions) => {
    try {
      if (options.dataType === 'reports' && interviewId) {
        // Interview-specific report export
        const templateType = getTemplateTypeFromDataType(options.dataType);
        const response = await apiFetch(`/conversations/reports/${interviewId}/export/${options.format}?template_type=${templateType}`);
        
        if (options.format === 'json') {
          // For JSON/markdown, response should be string content
          const content = typeof response === 'string' ? response : JSON.stringify(response, null, 2);
          downloadFromContent(content, options.fileName || `interview_${interviewId}_report`, options.format);
        } else {
          // PDF/Excel - use returned data
          const content = (response as any)?.content || response;
          downloadFromData(content, options.fileName || `interview_${interviewId}_report`, options.format);
        }
        
        addToast('Rapor başarıyla indirildi!', 'success');
        
      } else if (options.dataType === 'candidates' && jobId) {
        // Bulk candidate reports
        const templateType = getTemplateTypeFromDataType(options.dataType);
        const response = await apiFetch(`/conversations/reports/bulk/${jobId}/candidates?template_type=${templateType}`);
        
        // Convert bulk data to requested format
        const content = JSON.stringify(response, null, 2);
        downloadFromContent(content, options.fileName || `job_${jobId}_candidates`, 'json');
        
        const successCount = (response as any)?.successful_reports || 0;
        addToast(`${successCount} rapor başarıyla indirildi!`, 'success');
        
      } else {
        // Fallback to comprehensive report data
        const response = await apiFetch(`/conversations/analysis/${interviewId}`);
        const content = JSON.stringify(response, null, 2);
        downloadFromContent(content, options.fileName || `interview_${interviewId}_data`, 'json');
        
        addToast('Veri başarıyla indirildi!', 'success');
      }
      
    } catch (error) {
      console.error('Export failed:', error);
      addToast('Export işlemi başarısız oldu. Lütfen tekrar deneyin.', 'error');
      throw error;
    }
  };
  
  // Helper functions
  const getTemplateTypeFromDataType = (dataType: ExportDataType): string => {
    switch (dataType) {
      case 'reports': return 'executive_summary';
      case 'interviews': return 'detailed_technical';
      case 'candidates': return 'behavioral_focus';
      default: return 'executive_summary';
    }
  };
  

  
  const downloadFromData = (data: any, fileName: string, format: string) => {
    const content = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    downloadFromContent(content, fileName, format);
  };
  
  const downloadFromContent = (content: string, fileName: string, format: string) => {
    const mimeType = format === 'json' ? 'application/json' : 'text/plain';
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${fileName}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className={cn('relative', className)}>
      {/* Export Button */}
      <EnhancedButton
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        icon={
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        }
      >
        Dışa Aktar
      </EnhancedButton>

      {/* Export Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <EnhancedCard
            variant="elevated"
            className="w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto"
          >
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  Rapor Dışa Aktarma
                </h2>
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Export Format Selection */}
              <div className="space-y-3">
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Export Formatı
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {formatOptions.map((format) => (
                    <button
                      key={format.value}
                      onClick={() => setSelectedFormat(format.value)}
                      className={cn(
                        'p-4 border-2 rounded-lg text-left transition-all duration-200',
                        selectedFormat === format.value
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      )}
                    >
                      <div className="flex items-start space-x-3">
                        <span className="text-2xl">{format.icon}</span>
                        <div>
                          <div className={cn('font-medium', format.color)}>
                            {format.label}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            {format.description}
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Data Type Selection */}
              <div className="space-y-3">
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Veri Türü
                </h3>
                <div className="space-y-2">
                  {dataTypeOptions
                    .filter(option => availableDataTypes.includes(option.value))
                    .map((dataType) => (
                      <label
                        key={dataType.value}
                        className={cn(
                          'flex items-center p-3 border rounded-lg cursor-pointer transition-colors',
                          selectedDataType === dataType.value
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        )}
                      >
                        <input
                          type="radio"
                          name="dataType"
                          value={dataType.value}
                          checked={selectedDataType === dataType.value}
                          onChange={(e) => setSelectedDataType(e.target.value as ExportDataType)}
                          className="sr-only"
                        />
                        <div>
                          <div className="font-medium text-gray-900 dark:text-gray-100">
                            {dataType.label}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            {dataType.description}
                          </div>
                        </div>
                      </label>
                    ))}
                </div>
              </div>

              {/* Date Range */}
              <div className="space-y-3">
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Tarih Aralığı
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Başlangıç Tarihi
                    </label>
                    <input
                      type="date"
                      value={formatDate(dateRange.start)}
                      onChange={(e) => setDateRange(prev => ({ ...prev, start: new Date(e.target.value) }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Bitiş Tarihi
                    </label>
                    <input
                      type="date"
                      value={formatDate(dateRange.end)}
                      onChange={(e) => setDateRange(prev => ({ ...prev, end: new Date(e.target.value) }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
                    />
                  </div>
                </div>
              </div>

              {/* Options */}
              <div className="space-y-3">
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Seçenekler
                </h3>
                <div className="space-y-3">
                  {selectedFormat === 'pdf' && (
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={includeCharts}
                        onChange={(e) => setIncludeCharts(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        Grafikleri dahil et
                      </span>
                    </label>
                  )}
                  
                  <label className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      checked={includeRawData}
                      onChange={(e) => setIncludeRawData(e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      Ham verileri dahil et
                    </span>
                  </label>
                </div>
              </div>

              {/* File Name */}
              <div className="space-y-3">
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Dosya Adı
                </h3>
                <input
                  type="text"
                  value={fileName}
                  onChange={(e) => setFileName(e.target.value)}
                  placeholder={`${selectedDataType}_${formatDate(new Date())}`}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
                />
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <EnhancedButton
                  variant="ghost"
                  onClick={() => setIsOpen(false)}
                  disabled={isExporting}
                >
                  İptal
                </EnhancedButton>
                <EnhancedButton
                  variant="primary"
                  loading={isExporting}
                  onClick={() => handleRealExport({
                    format: selectedFormat,
                    dataType: selectedDataType,
                    dateRange,
                    includeCharts,
                    includeRawData,
                    fileName: fileName || `${selectedDataType}_${formatDate(new Date())}`,
                  })}
                  icon={
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                  }
                >
                  {isExporting ? 'Dışa Aktarılıyor...' : 'Dışa Aktar'}
                </EnhancedButton>
              </div>
            </div>
          </EnhancedCard>
        </div>
      )}
    </div>
  );
}

// Quick export buttons for common formats
interface QuickExportProps {
  onExport?: (format: ExportFormat) => void;
  loading?: boolean;
  className?: string;
}

export function QuickExportButtons({ onExport, loading = false, className }: QuickExportProps) {
  const quickFormats = [
    { format: 'pdf' as ExportFormat, label: 'PDF', icon: '📄', color: 'text-red-600' },
    { format: 'excel' as ExportFormat, label: 'Excel', icon: '📊', color: 'text-green-600' },
    { format: 'csv' as ExportFormat, label: 'CSV', icon: '📈', color: 'text-blue-600' },
  ];

  return (
    <div className={cn('flex items-center space-x-2', className)}>
      {quickFormats.map((format) => (
        <EnhancedButton
          key={format.format}
          size="sm"
          variant="outline"
          loading={loading}
          onClick={() => onExport?.(format.format)}
          icon={<span>{format.icon}</span>}
          className={format.color}
        >
          {format.label}
        </EnhancedButton>
      ))}
    </div>
  );
}

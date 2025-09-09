'use client';

import React, { useState, useCallback } from 'react';
import { EnhancedCard, EnhancedButton } from '@/components/ui';
import { cn } from '@/components/ui/utils/cn';

// Report Configuration Types
export interface ReportField {
  id: string;
  name: string;
  type: 'string' | 'number' | 'date' | 'boolean' | 'select';
  category: 'candidate' | 'interview' | 'job' | 'user' | 'system';
  aggregatable?: boolean;
  options?: string[]; // For select type
}

export interface ReportFilter {
  field: string;
  operator: 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'greater_than' | 'less_than' | 'between' | 'in' | 'not_in';
  value: any;
  label?: string;
}

export interface ReportGroupBy {
  field: string;
  timeFrame?: 'day' | 'week' | 'month' | 'quarter' | 'year';
}

export interface ReportConfig {
  id?: string;
  name: string;
  description?: string;
  fields: string[];
  filters: ReportFilter[];
  groupBy?: ReportGroupBy[];
  orderBy?: { field: string; direction: 'asc' | 'desc' }[];
  chartType?: 'table' | 'bar' | 'line' | 'pie' | 'area' | 'scatter';
  limit?: number;
  dateRange?: {
    start: Date;
    end: Date;
  };
}

// Available fields for reporting
const AVAILABLE_FIELDS: ReportField[] = [
  // Candidate fields
  { id: 'candidate_name', name: 'Aday Adı', type: 'string', category: 'candidate' },
  { id: 'candidate_email', name: 'Aday E-posta', type: 'string', category: 'candidate' },
  { id: 'candidate_score', name: 'Aday Skoru', type: 'number', category: 'candidate', aggregatable: true },
  { id: 'candidate_status', name: 'Aday Durumu', type: 'select', category: 'candidate', options: ['pending', 'completed', 'hired', 'rejected'] },
  
  // Interview fields
  { id: 'interview_duration', name: 'Mülakat Süresi', type: 'number', category: 'interview', aggregatable: true },
  { id: 'interview_date', name: 'Mülakat Tarihi', type: 'date', category: 'interview' },
  { id: 'interview_status', name: 'Mülakat Durumu', type: 'select', category: 'interview', options: ['scheduled', 'in_progress', 'completed', 'cancelled'] },
  { id: 'interview_questions_count', name: 'Soru Sayısı', type: 'number', category: 'interview', aggregatable: true },
  
  // Job fields
  { id: 'job_title', name: 'İş Pozisyonu', type: 'string', category: 'job' },
  { id: 'job_department', name: 'Departman', type: 'select', category: 'job', options: ['İK', 'Teknoloji', 'Pazarlama', 'Satış', 'Finans'] },
  { id: 'job_location', name: 'Lokasyon', type: 'string', category: 'job' },
  
  // System fields
  { id: 'created_at', name: 'Oluşturma Tarihi', type: 'date', category: 'system' },
  { id: 'updated_at', name: 'Güncelleme Tarihi', type: 'date', category: 'system' },
];

interface CustomReportBuilderProps {
  onSaveReport?: (config: ReportConfig) => void;
  onRunReport?: (config: ReportConfig) => void;
  initialConfig?: ReportConfig;
  className?: string;
}

export function CustomReportBuilder({
  onSaveReport,
  onRunReport,
  initialConfig,
  className,
}: CustomReportBuilderProps) {
  const [config, setConfig] = useState<ReportConfig>(
    initialConfig || {
      name: '',
      description: '',
      fields: [],
      filters: [],
      groupBy: [],
      orderBy: [],
      chartType: 'table',
      limit: 100,
    }
  );

  const [activeTab, setActiveTab] = useState<'fields' | 'filters' | 'grouping' | 'visualization'>('fields');
  const [isPreviewMode, setIsPreviewMode] = useState(false);

  // Field selection handlers
  const toggleField = useCallback((fieldId: string) => {
    setConfig(prev => ({
      ...prev,
      fields: prev.fields.includes(fieldId)
        ? prev.fields.filter(id => id !== fieldId)
        : [...prev.fields, fieldId],
    }));
  }, []);

  // Filter management
  const addFilter = useCallback(() => {
    setConfig(prev => ({
      ...prev,
      filters: [
        ...prev.filters,
        {
          field: '',
          operator: 'equals',
          value: '',
        },
      ],
    }));
  }, []);

  const updateFilter = useCallback((index: number, filter: Partial<ReportFilter>) => {
    setConfig(prev => ({
      ...prev,
      filters: prev.filters.map((f, i) => i === index ? { ...f, ...filter } : f),
    }));
  }, []);

  const removeFilter = useCallback((index: number) => {
    setConfig(prev => ({
      ...prev,
      filters: prev.filters.filter((_, i) => i !== index),
    }));
  }, []);

  // Group by management
  const addGroupBy = useCallback(() => {
    setConfig(prev => ({
      ...prev,
      groupBy: [
        ...(prev.groupBy || []),
        { field: '' },
      ],
    }));
  }, []);

  const updateGroupBy = useCallback((index: number, groupBy: Partial<ReportGroupBy>) => {
    setConfig(prev => ({
      ...prev,
      groupBy: (prev.groupBy || []).map((g, i) => i === index ? { ...g, ...groupBy } : g),
    }));
  }, []);

  const removeGroupBy = useCallback((index: number) => {
    setConfig(prev => ({
      ...prev,
      groupBy: (prev.groupBy || []).filter((_, i) => i !== index),
    }));
  }, []);

  // Get field by ID
  const getField = (fieldId: string) => AVAILABLE_FIELDS.find(f => f.id === fieldId);

  // Get operator options based on field type
  const getOperatorOptions = (fieldType: string) => {
    switch (fieldType) {
      case 'string':
        return [
          { value: 'equals', label: 'Eşittir' },
          { value: 'not_equals', label: 'Eşit değildir' },
          { value: 'contains', label: 'İçerir' },
          { value: 'not_contains', label: 'İçermez' },
        ];
      case 'number':
        return [
          { value: 'equals', label: 'Eşittir' },
          { value: 'not_equals', label: 'Eşit değildir' },
          { value: 'greater_than', label: 'Büyüktür' },
          { value: 'less_than', label: 'Küçüktür' },
          { value: 'between', label: 'Arasında' },
        ];
      case 'date':
        return [
          { value: 'equals', label: 'Eşittir' },
          { value: 'greater_than', label: 'Sonra' },
          { value: 'less_than', label: 'Önce' },
          { value: 'between', label: 'Arasında' },
        ];
      case 'select':
        return [
          { value: 'in', label: 'İçinde' },
          { value: 'not_in', label: 'İçinde değil' },
        ];
      default:
        return [{ value: 'equals', label: 'Eşittir' }];
    }
  };

  // Group fields by category
  const fieldsByCategory = AVAILABLE_FIELDS.reduce((acc, field) => {
    if (!acc[field.category]) acc[field.category] = [];
    acc[field.category].push(field);
    return acc;
  }, {} as Record<string, ReportField[]>);

  const categoryLabels = {
    candidate: 'Aday Bilgileri',
    interview: 'Mülakat Verileri',
    job: 'İş İlanları',
    user: 'Kullanıcılar',
    system: 'Sistem',
  };

  // Tabs configuration
  const tabs = [
    { id: 'fields', label: 'Alanlar', icon: '📋' },
    { id: 'filters', label: 'Filtreler', icon: '🔍' },
    { id: 'grouping', label: 'Gruplama', icon: '📊' },
    { id: 'visualization', label: 'Görselleştirme', icon: '📈' },
  ];

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <EnhancedCard variant="elevated" padding="md">
        <div className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Özel Rapor Oluşturucu
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              İhtiyacınıza özel raporlar oluşturun ve analizlerinizi derinleştirin
            </p>
          </div>

          {/* Report Name & Description */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Rapor Adı
              </label>
              <input
                type="text"
                value={config.name}
                onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Rapor adını girin"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Açıklama (Opsiyonel)
              </label>
              <input
                type="text"
                value={config.description}
                onChange={(e) => setConfig(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Rapor açıklaması"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>
          </div>
        </div>
      </EnhancedCard>

      {/* Tabs Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={cn(
                'py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2',
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              )}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {/* Fields Tab */}
        {activeTab === 'fields' && (
          <EnhancedCard variant="default" padding="md">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Raporda Gösterilecek Alanlar
                </h3>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {config.fields.length} alan seçildi
                </span>
              </div>

              {Object.entries(fieldsByCategory).map(([category, fields]) => (
                <div key={category} className="space-y-3">
                  <h4 className="font-medium text-gray-700 dark:text-gray-300">
                    {categoryLabels[category as keyof typeof categoryLabels]}
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {fields.map((field) => (
                      <label
                        key={field.id}
                        className={cn(
                          'flex items-center space-x-3 p-3 border rounded-lg cursor-pointer transition-colors',
                          config.fields.includes(field.id)
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={config.fields.includes(field.id)}
                          onChange={() => toggleField(field.id)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <div>
                          <div className="font-medium text-gray-900 dark:text-gray-100">
                            {field.name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {field.type} {field.aggregatable && '• Toplanabilir'}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </EnhancedCard>
        )}

        {/* Filters Tab */}
        {activeTab === 'filters' && (
          <EnhancedCard variant="default" padding="md">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Veri Filtreleri
                </h3>
                <EnhancedButton
                  size="sm"
                  variant="outline"
                  onClick={addFilter}
                  icon={
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                  }
                >
                  Filtre Ekle
                </EnhancedButton>
              </div>

              {config.filters.length === 0 && (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.414A1 1 0 013 6.707V4z" />
                  </svg>
                  <p>Henüz filtre eklenmedi</p>
                  <p className="text-sm mt-1">Yukarıdaki &quot;Filtre Ekle&quot; butonunu kullanarak filtre ekleyin</p>
                </div>
              )}

              <div className="space-y-4">
                {config.filters.map((filter, index) => (
                  <div
                    key={index}
                    className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg space-y-4"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Filtre #{index + 1}
                      </span>
                      <button
                        onClick={() => removeFilter(index)}
                        className="text-red-600 hover:text-red-700 dark:text-red-400"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {/* Field Selection */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Alan
                        </label>
                        <select
                          value={filter.field}
                          onChange={(e) => updateFilter(index, { field: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
                        >
                          <option value="">Alan seçin</option>
                          {Object.entries(fieldsByCategory).map(([category, fields]) => (
                            <optgroup key={category} label={categoryLabels[category as keyof typeof categoryLabels]}>
                              {fields.map((field) => (
                                <option key={field.id} value={field.id}>
                                  {field.name}
                                </option>
                              ))}
                            </optgroup>
                          ))}
                        </select>
                      </div>

                      {/* Operator Selection */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Operatör
                        </label>
                        <select
                          value={filter.operator}
                          onChange={(e) => updateFilter(index, { operator: e.target.value as any })}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
                          disabled={!filter.field}
                        >
                          {filter.field && getOperatorOptions(getField(filter.field)?.type || 'string').map((op) => (
                            <option key={op.value} value={op.value}>
                              {op.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Value Input */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Değer
                        </label>
                        {filter.field && getField(filter.field)?.type === 'select' ? (
                          <select
                            value={filter.value}
                            onChange={(e) => updateFilter(index, { value: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
                          >
                            <option value="">Değer seçin</option>
                            {getField(filter.field)?.options?.map((option) => (
                              <option key={option} value={option}>
                                {option}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type={getField(filter.field)?.type === 'date' ? 'date' : getField(filter.field)?.type === 'number' ? 'number' : 'text'}
                            value={filter.value}
                            onChange={(e) => updateFilter(index, { value: e.target.value })}
                            placeholder="Değer girin"
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
                          />
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </EnhancedCard>
        )}

        {/* Grouping Tab */}
        {activeTab === 'grouping' && (
          <EnhancedCard variant="default" padding="md">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  Gruplama ve Sıralama
                </h3>
                <EnhancedButton
                  size="sm"
                  variant="outline"
                  onClick={addGroupBy}
                  icon={
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                  }
                >
                  Gruplama Ekle
                </EnhancedButton>
              </div>

              {/* Group By */}
              <div className="space-y-4">
                {(config.groupBy || []).map((groupBy, index) => (
                  <div
                    key={index}
                    className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Gruplama #{index + 1}
                      </span>
                      <button
                        onClick={() => removeGroupBy(index)}
                        className="text-red-600 hover:text-red-700 dark:text-red-400"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Alan
                        </label>
                        <select
                          value={groupBy.field}
                          onChange={(e) => updateGroupBy(index, { field: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
                        >
                          <option value="">Alan seçin</option>
                          {config.fields.map((fieldId) => {
                            const field = getField(fieldId);
                            return field ? (
                              <option key={field.id} value={field.id}>
                                {field.name}
                              </option>
                            ) : null;
                          })}
                        </select>
                      </div>

                      {groupBy.field && getField(groupBy.field)?.type === 'date' && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Zaman Aralığı
                          </label>
                          <select
                            value={groupBy.timeFrame || ''}
                            onChange={(e) => updateGroupBy(index, { timeFrame: e.target.value as any })}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
                          >
                            <option value="">Zaman aralığı seçin</option>
                            <option value="day">Günlük</option>
                            <option value="week">Haftalık</option>
                            <option value="month">Aylık</option>
                            <option value="quarter">Çeyreklik</option>
                            <option value="year">Yıllık</option>
                          </select>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </EnhancedCard>
        )}

        {/* Visualization Tab */}
        {activeTab === 'visualization' && (
          <EnhancedCard variant="default" padding="md">
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                Görselleştirme Ayarları
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Chart Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                    Grafik Türü
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { value: 'table', label: 'Tablo', icon: '📋' },
                      { value: 'bar', label: 'Sütun Grafik', icon: '📊' },
                      { value: 'line', label: 'Çizgi Grafik', icon: '📈' },
                      { value: 'pie', label: 'Pasta Grafik', icon: '🥧' },
                      { value: 'area', label: 'Alan Grafik', icon: '📉' },
                      { value: 'scatter', label: 'Nokta Grafik', icon: '⚪' },
                    ].map((type) => (
                      <label
                        key={type.value}
                        className={cn(
                          'flex items-center space-x-2 p-3 border rounded-lg cursor-pointer transition-colors',
                          config.chartType === type.value
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        )}
                      >
                        <input
                          type="radio"
                          name="chartType"
                          value={type.value}
                          checked={config.chartType === type.value}
                          onChange={(e) => setConfig(prev => ({ ...prev, chartType: e.target.value as any }))}
                          className="sr-only"
                        />
                        <span className="text-lg">{type.icon}</span>
                        <span className="text-sm font-medium">{type.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Limit */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Kayıt Limiti
                  </label>
                  <select
                    value={config.limit}
                    onChange={(e) => setConfig(prev => ({ ...prev, limit: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100"
                  >
                    <option value={25}>25 kayıt</option>
                    <option value={50}>50 kayıt</option>
                    <option value={100}>100 kayıt</option>
                    <option value={500}>500 kayıt</option>
                    <option value={1000}>1000 kayıt</option>
                    <option value={0}>Tümü (limit yok)</option>
                  </select>
                </div>
              </div>
            </div>
          </EnhancedCard>
        )}
      </div>

      {/* Actions */}
      <EnhancedCard variant="elevated" padding="md">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setIsPreviewMode(!isPreviewMode)}
              className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 dark:text-blue-400"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <span className="text-sm">
                {isPreviewMode ? 'Önizlemeyi Kapat' : 'Önizleme'}
              </span>
            </button>
          </div>
          
          <div className="flex items-center space-x-3">
            <EnhancedButton
              variant="outline"
              onClick={() => onSaveReport?.(config)}
              disabled={!config.name || config.fields.length === 0}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              }
            >
              Raporu Kaydet
            </EnhancedButton>
            
            <EnhancedButton
              variant="primary"
              onClick={() => onRunReport?.(config)}
              disabled={!config.name || config.fields.length === 0}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h8m2 2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v11a2 2 0 002 2z" />
                </svg>
              }
            >
              Raporu Çalıştır
            </EnhancedButton>
          </div>
        </div>

        {/* Preview Mode */}
        {isPreviewMode && (
          <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <div className="space-y-4">
              <h4 className="font-medium text-gray-900 dark:text-gray-100">
                Rapor Önizlemesi
              </h4>
              
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-3">
                <div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Adı:</span>
                  <span className="ml-2 text-sm text-gray-900 dark:text-gray-100">
                    {config.name || 'Başlıksız Rapor'}
                  </span>
                </div>
                
                <div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Alanlar:</span>
                  <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                    {config.fields.length > 0 
                      ? config.fields.map(fieldId => getField(fieldId)?.name).join(', ')
                      : 'Hiç alan seçilmedi'
                    }
                  </span>
                </div>
                
                <div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filtreler:</span>
                  <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                    {config.filters.length} filtre
                  </span>
                </div>
                
                <div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Görselleştirme:</span>
                  <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                    {config.chartType === 'table' ? 'Tablo' : 
                     config.chartType === 'bar' ? 'Sütun Grafik' :
                     config.chartType === 'line' ? 'Çizgi Grafik' :
                     config.chartType === 'pie' ? 'Pasta Grafik' :
                     config.chartType === 'area' ? 'Alan Grafik' : 'Nokta Grafik'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </EnhancedCard>
    </div>
  );
}

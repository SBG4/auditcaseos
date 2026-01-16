import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  DocumentArrowDownIcon,
  DocumentTextIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { casesApi, reportsApi } from '../services/api';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Card, { CardHeader } from '../components/common/Card';
import type { Case, ReportTemplate } from '../types';

export default function Reports() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplate>('STANDARD');
  const [generatingFor, setGeneratingFor] = useState<string | null>(null);

  const { data: casesData, isLoading } = useQuery({
    queryKey: ['cases', { page_size: 100 }],
    queryFn: () => casesApi.list({ page_size: 100 }),
  });

  // Templates are predefined, no need to fetch from API
  // const { data: templatesData } = useQuery({
  //   queryKey: ['report-templates'],
  //   queryFn: () => reportsApi.templates(),
  // });

  const handleGenerateReport = async (caseItem: Case) => {
    setGeneratingFor(caseItem.id);
    try {
      const blob = await reportsApi.generate(caseItem.id, {
        template: selectedTemplate,
        include_evidence: true,
        include_similar: true,
        include_ai_summary: true,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${caseItem.case_id}_${selectedTemplate.toLowerCase()}_report.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to generate report:', error);
      alert('Failed to generate report. Please try again.');
    } finally {
      setGeneratingFor(null);
    }
  };

  const filteredCases = casesData?.items.filter((caseItem) => {
    const matchesSearch =
      !searchTerm ||
      caseItem.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      caseItem.case_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = !statusFilter || caseItem.status === statusFilter;
    return matchesSearch && matchesStatus;
  }) || [];

  const templates: { id: ReportTemplate; name: string; description: string; color: string }[] = [
    {
      id: 'STANDARD',
      name: 'Standard Report',
      description: 'Full case report with all sections including evidence, findings, and timeline',
      color: 'primary',
    },
    {
      id: 'EXECUTIVE_SUMMARY',
      name: 'Executive Summary',
      description: 'Brief overview for management with key points and risk assessment',
      color: 'blue',
    },
    {
      id: 'DETAILED',
      name: 'Detailed Report',
      description: 'Comprehensive investigation report with entities and similar cases',
      color: 'green',
    },
    {
      id: 'COMPLIANCE',
      name: 'Compliance Report',
      description: 'Regulatory compliance focused report with detailed findings',
      color: 'purple',
    },
  ];

  const getColorClasses = (color: string, selected: boolean) => {
    const colors: Record<string, { border: string; bg: string; text: string }> = {
      primary: {
        border: selected ? 'border-primary-500' : 'border-gray-200',
        bg: selected ? 'bg-primary-50' : 'bg-white',
        text: 'text-primary-600',
      },
      blue: {
        border: selected ? 'border-blue-500' : 'border-gray-200',
        bg: selected ? 'bg-blue-50' : 'bg-white',
        text: 'text-blue-600',
      },
      green: {
        border: selected ? 'border-green-500' : 'border-gray-200',
        bg: selected ? 'bg-green-50' : 'bg-white',
        text: 'text-green-600',
      },
      purple: {
        border: selected ? 'border-purple-500' : 'border-gray-200',
        bg: selected ? 'bg-purple-50' : 'bg-white',
        text: 'text-purple-600',
      },
    };
    return colors[color] || colors.primary;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="mt-1 text-sm text-gray-500">
          Generate DOCX reports for audit cases
        </p>
      </div>

      {/* Template Selection */}
      <Card>
        <CardHeader title="Select Report Template" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {templates.map((template) => {
            const isSelected = selectedTemplate === template.id;
            const colors = getColorClasses(template.color, isSelected);
            return (
              <button
                key={template.id}
                onClick={() => setSelectedTemplate(template.id)}
                className={`p-4 border-2 rounded-lg transition-all text-left ${colors.border} ${colors.bg}`}
              >
                <DocumentTextIcon className={`w-8 h-8 ${colors.text} mb-2`} />
                <h3 className="font-medium text-gray-900">{template.name}</h3>
                <p className="text-xs text-gray-500 mt-1">{template.description}</p>
                {isSelected && (
                  <span className={`inline-block mt-2 text-xs font-medium ${colors.text}`}>
                    Selected
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </Card>

      {/* Filters */}
      <Card>
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search cases by title or case ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input pl-10"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <FunnelIcon className="w-5 h-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="CLOSED">Closed</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Cases List */}
      <Card>
        <CardHeader
          title="Select Case"
          subtitle={`${filteredCases.length} cases available for report generation`}
        />
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="text-center py-12">
            <DocumentTextIcon className="w-12 h-12 text-gray-300 mx-auto" />
            <p className="mt-4 text-gray-500">No cases found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Case
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Severity
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Stats
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredCases.map((caseItem) => (
                  <tr key={caseItem.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4">
                      <div>
                        <p className="font-medium text-gray-900">{caseItem.title}</p>
                        <p className="text-sm text-gray-500 font-mono">{caseItem.case_id}</p>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <Badge variant="status" value={caseItem.status} />
                    </td>
                    <td className="px-4 py-4">
                      <Badge variant="severity" value={caseItem.severity} />
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-500">
                      {format(new Date(caseItem.created_at), 'PP')}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex gap-4 text-sm text-gray-500">
                        <span>{caseItem.evidence_count} evidence</span>
                        <span>{caseItem.findings_count} findings</span>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right">
                      <Button
                        size="sm"
                        onClick={() => handleGenerateReport(caseItem)}
                        isLoading={generatingFor === caseItem.id}
                        disabled={generatingFor !== null}
                      >
                        <DocumentArrowDownIcon className="w-4 h-4 mr-2" />
                        Generate
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Help Section */}
      <Card>
        <CardHeader title="Report Information" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-900 mb-2">What's Included</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>- Cover page with case ID and classification</li>
              <li>- Executive summary (AI-generated)</li>
              <li>- Case details and metadata</li>
              <li>- Timeline of events</li>
              <li>- Findings with severity ratings</li>
              <li>- Evidence list with file hashes</li>
              <li>- Similar cases (if available)</li>
              <li>- Extracted entities appendix</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Template Differences</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li><strong>Standard:</strong> All sections, balanced detail</li>
              <li><strong>Executive:</strong> Summary focus, key points only</li>
              <li><strong>Detailed:</strong> Maximum detail, all appendices</li>
              <li><strong>Compliance:</strong> Regulatory focus, control mappings</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}

import { useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  ArrowLeftIcon,
  PencilIcon,
  TrashIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  ClockIcon,
  SparklesIcon,
  DocumentArrowDownIcon,
  ArrowUpTrayIcon,
  UserIcon,
  ComputerDesktopIcon,
  FolderOpenIcon,
} from '@heroicons/react/24/outline';
import { casesApi, evidenceApi, findingsApi, timelineApi, aiApi, reportsApi, nextcloudApi } from '../services/api';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Card, { CardHeader } from '../components/common/Card';
import type { Evidence, Finding, TimelineEvent, CaseStatus, Severity } from '../types';

type TabType = 'overview' | 'evidence' | 'findings' | 'timeline' | 'ai';

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [isEditing, setIsEditing] = useState(false);
  const [uploadDescription, setUploadDescription] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: caseData, isLoading } = useQuery({
    queryKey: ['case', id],
    queryFn: () => casesApi.get(id!),
    enabled: !!id,
  });

  const { data: evidenceData, refetch: refetchEvidence } = useQuery({
    queryKey: ['evidence', id],
    queryFn: () => evidenceApi.list(id!),
    enabled: !!id && activeTab === 'evidence',
  });

  const { data: findingsData } = useQuery({
    queryKey: ['findings', id],
    queryFn: () => findingsApi.list(id!),
    enabled: !!id && activeTab === 'findings',
  });

  const { data: timelineData } = useQuery({
    queryKey: ['timeline', id],
    queryFn: () => timelineApi.list(id!),
    enabled: !!id && activeTab === 'timeline',
  });

  const { data: aiSummary, isLoading: aiLoading, refetch: refetchAiSummary } = useQuery({
    queryKey: ['ai-summary', id],
    queryFn: () => aiApi.summarize(id!),
    enabled: !!id && activeTab === 'ai',
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
    retry: false,
  });

  const { data: nextcloudUrl } = useQuery({
    queryKey: ['nextcloud-url', id],
    queryFn: () => nextcloudApi.getCaseFolderUrl(id!),
    enabled: !!id,
    retry: false,
    staleTime: 1000 * 60 * 30, // Cache for 30 minutes
  });

  const deleteCase = useMutation({
    mutationFn: () => casesApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      navigate('/cases');
    },
  });

  const updateCase = useMutation({
    mutationFn: (data: { status?: CaseStatus; severity?: Severity }) =>
      casesApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case', id] });
      setIsEditing(false);
    },
  });

  const uploadEvidence = useMutation({
    mutationFn: async (file: File) => {
      return evidenceApi.upload(id!, file, uploadDescription || undefined);
    },
    onSuccess: () => {
      refetchEvidence();
      setUploadDescription('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
  });

  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  const handleGenerateReport = async (template: string = 'STANDARD') => {
    setIsGeneratingReport(true);
    try {
      const blob = await reportsApi.generate(id!, { template: template as any });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${caseData?.case_id || id}_report.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to generate report:', error);
      alert('Failed to generate report. Please try again.');
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadEvidence.mutate(file);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Case not found</p>
        <Button className="mt-4" onClick={() => navigate('/cases')}>
          Back to Cases
        </Button>
      </div>
    );
  }

  const tabs: { id: TabType; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: 'overview', label: 'Overview', icon: DocumentTextIcon },
    { id: 'evidence', label: 'Evidence', icon: ClipboardDocumentListIcon },
    { id: 'findings', label: 'Findings', icon: DocumentTextIcon },
    { id: 'timeline', label: 'Timeline', icon: ClockIcon },
    { id: 'ai', label: 'AI Analysis', icon: SparklesIcon },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <button
            onClick={() => navigate('/cases')}
            className="p-2 hover:bg-gray-100 rounded-md transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5 text-gray-500" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{caseData.title}</h1>
              <Badge variant="status" value={caseData.status} />
              <Badge variant="severity" value={caseData.severity} />
            </div>
            <p className="mt-1 text-sm text-gray-500">{caseData.case_id}</p>
          </div>
        </div>
        <div className="flex gap-2">
          {nextcloudUrl?.url && (
            <Button
              variant="secondary"
              onClick={() => window.open(nextcloudUrl.url, '_blank')}
            >
              <FolderOpenIcon className="w-4 h-4 mr-2" />
              Nextcloud
            </Button>
          )}
          <div className="relative">
            <Button
              variant="secondary"
              onClick={() => handleGenerateReport()}
              isLoading={isGeneratingReport}
            >
              <DocumentArrowDownIcon className="w-4 h-4 mr-2" />
              Report
            </Button>
          </div>
          <Button variant="secondary" onClick={() => setIsEditing(!isEditing)}>
            <PencilIcon className="w-4 h-4 mr-2" />
            Edit
          </Button>
          <Button
            variant="danger"
            onClick={() => {
              if (confirm('Are you sure you want to archive this case?')) {
                deleteCase.mutate();
              }
            }}
          >
            <TrashIcon className="w-4 h-4 mr-2" />
            Archive
          </Button>
        </div>
      </div>

      {/* Edit Panel */}
      {isEditing && (
        <Card>
          <CardHeader title="Edit Case" />
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Status</label>
              <select
                value={caseData.status}
                onChange={(e) =>
                  updateCase.mutate({ status: e.target.value as CaseStatus })
                }
                className="input mt-1"
              >
                <option value="OPEN">Open</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="PENDING_REVIEW">Pending Review</option>
                <option value="CLOSED">Closed</option>
                <option value="ARCHIVED">Archived</option>
              </select>
            </div>
            <div>
              <label className="label">Severity</label>
              <select
                value={caseData.severity}
                onChange={(e) =>
                  updateCase.mutate({ severity: e.target.value as Severity })
                }
                className="input mt-1"
              >
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
                <option value="INFO">Info</option>
              </select>
            </div>
          </div>
        </Card>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center py-4 px-1 border-b-2 text-sm font-medium transition-colors
                ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              <tab.icon className="w-5 h-5 mr-2" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader title="Summary" />
              <p className="text-gray-700 whitespace-pre-wrap">
                {caseData.summary || 'No summary provided'}
              </p>
            </Card>
            <Card>
              <CardHeader title="Description" />
              <p className="text-gray-700 whitespace-pre-wrap">
                {caseData.description || 'No description provided'}
              </p>
            </Card>
          </div>
          <div className="space-y-6">
            <Card>
              <CardHeader title="Case Details" />
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm text-gray-500">Case ID</dt>
                  <dd className="text-sm font-medium text-gray-900 font-mono">
                    {caseData.case_id}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Type</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {caseData.case_type}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Scope</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {caseData.scope_code}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Owner</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {caseData.owner?.full_name || 'Unknown'}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Created</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {format(new Date(caseData.created_at), 'PPpp')}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Updated</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {format(new Date(caseData.updated_at), 'PPpp')}
                  </dd>
                </div>
              </dl>
            </Card>

            {/* Subject Details */}
            {(caseData.subject_user || caseData.subject_computer) && (
              <Card>
                <CardHeader title="Subject" />
                <dl className="space-y-3">
                  {caseData.subject_user && (
                    <div className="flex items-center gap-2">
                      <UserIcon className="w-4 h-4 text-gray-400" />
                      <div>
                        <dt className="text-xs text-gray-500">User</dt>
                        <dd className="text-sm font-medium text-gray-900">
                          {caseData.subject_user}
                        </dd>
                      </div>
                    </div>
                  )}
                  {caseData.subject_computer && (
                    <div className="flex items-center gap-2">
                      <ComputerDesktopIcon className="w-4 h-4 text-gray-400" />
                      <div>
                        <dt className="text-xs text-gray-500">Computer</dt>
                        <dd className="text-sm font-medium text-gray-900 font-mono">
                          {caseData.subject_computer}
                        </dd>
                      </div>
                    </div>
                  )}
                </dl>
              </Card>
            )}

            {/* Tags */}
            {caseData.tags && caseData.tags.length > 0 && (
              <Card>
                <CardHeader title="Tags" />
                <div className="flex flex-wrap gap-2">
                  {caseData.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </Card>
            )}

            {/* Statistics */}
            <Card>
              <CardHeader title="Statistics" />
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-gray-900">
                    {caseData.evidence_count}
                  </div>
                  <div className="text-xs text-gray-500">Evidence</div>
                </div>
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-gray-900">
                    {caseData.findings_count}
                  </div>
                  <div className="text-xs text-gray-500">Findings</div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {activeTab === 'evidence' && (
        <div className="space-y-6">
          {/* Upload Section */}
          <Card>
            <CardHeader title="Upload Evidence" />
            <div className="space-y-4">
              <div>
                <label className="label">Description (optional)</label>
                <input
                  type="text"
                  value={uploadDescription}
                  onChange={(e) => setUploadDescription(e.target.value)}
                  placeholder="Brief description of the evidence"
                  className="input mt-1"
                />
              </div>
              <div className="flex items-center gap-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="evidence-upload"
                />
                <label htmlFor="evidence-upload">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => fileInputRef.current?.click()}
                    isLoading={uploadEvidence.isPending}
                  >
                    <ArrowUpTrayIcon className="w-4 h-4 mr-2" />
                    Choose File
                  </Button>
                </label>
                <span className="text-sm text-gray-500">
                  Supported: PDF, Images, Documents, Text files
                </span>
              </div>
            </div>
          </Card>

          {/* Evidence List */}
          <Card>
            <CardHeader title="Evidence" subtitle={`${evidenceData?.length || 0} items`} />
            {!evidenceData || evidenceData.length === 0 ? (
              <p className="text-gray-500 text-sm">No evidence attached</p>
            ) : (
              <div className="space-y-3">
                {evidenceData.map((item: Evidence) => (
                  <div
                    key={item.id}
                    className="p-4 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{item.file_name}</p>
                        <div className="flex items-center gap-4 mt-1">
                          <span className="text-sm text-gray-500">{item.mime_type}</span>
                          <span className="text-sm text-gray-500">
                            {(item.file_size / 1024).toFixed(1)} KB
                          </span>
                        </div>
                      </div>
                      <Badge value={item.evidence_type} />
                    </div>
                    {item.description && (
                      <p className="mt-2 text-sm text-gray-600">{item.description}</p>
                    )}
                    {item.file_hash && (
                      <p className="mt-2 text-xs text-gray-400 font-mono truncate">
                        SHA256: {item.file_hash}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {activeTab === 'findings' && (
        <Card>
          <CardHeader title="Findings" subtitle={`${findingsData?.length || 0} items`} />
          {!findingsData || findingsData.length === 0 ? (
            <p className="text-gray-500 text-sm">No findings recorded</p>
          ) : (
            <div className="space-y-3">
              {findingsData.map((finding: Finding) => (
                <div
                  key={finding.id}
                  className="p-4 border border-gray-200 rounded-lg"
                >
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium text-gray-900">{finding.title}</p>
                    <div className="flex gap-2">
                      <Badge variant="severity" value={finding.severity} />
                      <Badge value={finding.finding_type} />
                    </div>
                  </div>
                  {finding.description && (
                    <p className="text-sm text-gray-600">{finding.description}</p>
                  )}
                  <p className="mt-2 text-xs text-gray-400">
                    Added {format(new Date(finding.created_at), 'PPp')}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {activeTab === 'timeline' && (
        <Card>
          <CardHeader title="Timeline" subtitle="Case activity history" />
          {!timelineData || timelineData.length === 0 ? (
            <p className="text-gray-500 text-sm">No timeline events</p>
          ) : (
            <div className="space-y-4">
              {timelineData.map((event: TimelineEvent, index: number) => (
                <div key={event.id} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="w-3 h-3 bg-primary-500 rounded-full"></div>
                    {index < timelineData.length - 1 && (
                      <div className="w-0.5 flex-1 bg-gray-200 mt-2"></div>
                    )}
                  </div>
                  <div className="flex-1 pb-4">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-gray-900">{event.event_type}</p>
                      {event.source && (
                        <span className="text-xs px-2 py-0.5 bg-gray-100 rounded">
                          {event.source}
                        </span>
                      )}
                    </div>
                    {event.description && (
                      <p className="text-sm text-gray-600 mt-1">
                        {event.description}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">
                      {format(new Date(event.event_time), 'PPpp')}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {activeTab === 'ai' && (
        <div className="space-y-6">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <CardHeader title="AI-Generated Summary" subtitle="Powered by Ollama" />
              <Button
                variant="secondary"
                size="sm"
                onClick={() => refetchAiSummary()}
                isLoading={aiLoading}
              >
                <SparklesIcon className="w-4 h-4 mr-2" />
                Regenerate
              </Button>
            </div>
            {aiLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
                  <p className="mt-4 text-gray-500">Generating AI summary...</p>
                  <p className="text-sm text-gray-400">This may take a moment</p>
                </div>
              </div>
            ) : aiSummary ? (
              <div className="space-y-6">
                {/* Summary */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Summary</h4>
                  <p className="text-gray-600">{aiSummary.summary}</p>
                </div>

                {/* Key Points */}
                {aiSummary.key_points && aiSummary.key_points.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Key Points</h4>
                    <ul className="list-disc list-inside space-y-1">
                      {aiSummary.key_points.map((point, idx) => (
                        <li key={idx} className="text-gray-600">{point}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Risk Assessment */}
                {aiSummary.risk_assessment && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Risk Assessment</h4>
                    <p className="text-gray-600">{aiSummary.risk_assessment}</p>
                  </div>
                )}

                {/* Recommendations */}
                {aiSummary.recommended_actions && aiSummary.recommended_actions.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Recommended Actions</h4>
                    <ul className="list-disc list-inside space-y-1">
                      {aiSummary.recommended_actions.map((action, idx) => (
                        <li key={idx} className="text-gray-600">{action}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Metadata */}
                <div className="pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>Model: {aiSummary.model_used}</span>
                    <span>Confidence: {(aiSummary.confidence_score * 100).toFixed(0)}%</span>
                    <span>Generated: {format(new Date(aiSummary.generated_at), 'PPp')}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <SparklesIcon className="w-12 h-12 text-gray-300 mx-auto" />
                <p className="mt-4 text-gray-500">Click "Regenerate" to generate an AI summary</p>
              </div>
            )}
          </Card>

          {/* Report Generation */}
          <Card>
            <CardHeader title="Generate Report" subtitle="Download case report as DOCX" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <button
                onClick={() => handleGenerateReport('STANDARD')}
                disabled={isGeneratingReport}
                className="p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors text-left"
              >
                <DocumentArrowDownIcon className="w-8 h-8 text-primary-600 mb-2" />
                <h5 className="font-medium text-gray-900">Standard</h5>
                <p className="text-xs text-gray-500">Full case report</p>
              </button>
              <button
                onClick={() => handleGenerateReport('EXECUTIVE_SUMMARY')}
                disabled={isGeneratingReport}
                className="p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors text-left"
              >
                <DocumentArrowDownIcon className="w-8 h-8 text-blue-600 mb-2" />
                <h5 className="font-medium text-gray-900">Executive</h5>
                <p className="text-xs text-gray-500">Brief overview</p>
              </button>
              <button
                onClick={() => handleGenerateReport('DETAILED')}
                disabled={isGeneratingReport}
                className="p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors text-left"
              >
                <DocumentArrowDownIcon className="w-8 h-8 text-green-600 mb-2" />
                <h5 className="font-medium text-gray-900">Detailed</h5>
                <p className="text-xs text-gray-500">Comprehensive</p>
              </button>
              <button
                onClick={() => handleGenerateReport('COMPLIANCE')}
                disabled={isGeneratingReport}
                className="p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors text-left"
              >
                <DocumentArrowDownIcon className="w-8 h-8 text-purple-600 mb-2" />
                <h5 className="font-medium text-gray-900">Compliance</h5>
                <p className="text-xs text-gray-500">Regulatory focus</p>
              </button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

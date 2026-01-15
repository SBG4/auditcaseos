import { useState } from 'react';
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
} from '@heroicons/react/24/outline';
import { casesApi, evidenceApi, findingsApi, timelineApi } from '../services/api';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Card, { CardHeader } from '../components/common/Card';
import type { Evidence, Finding, TimelineEvent, CaseStatus, Severity } from '../types';

type TabType = 'overview' | 'evidence' | 'findings' | 'timeline';

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [isEditing, setIsEditing] = useState(false);

  const { data: caseData, isLoading } = useQuery({
    queryKey: ['case', id],
    queryFn: () => casesApi.get(id!),
    enabled: !!id,
  });

  const { data: evidenceData } = useQuery({
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
            <p className="mt-1 text-sm text-gray-500">{caseData.case_number}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setIsEditing(!isEditing)}>
            <PencilIcon className="w-4 h-4 mr-2" />
            Edit
          </Button>
          <Button
            variant="danger"
            onClick={() => {
              if (confirm('Are you sure you want to delete this case?')) {
                deleteCase.mutate();
              }
            }}
          >
            <TrashIcon className="w-4 h-4 mr-2" />
            Delete
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
          <div className="lg:col-span-2">
            <Card>
              <CardHeader title="Description" />
              <p className="text-gray-700 whitespace-pre-wrap">
                {caseData.description || 'No description provided'}
              </p>
            </Card>
          </div>
          <div className="space-y-6">
            <Card>
              <CardHeader title="Details" />
              <dl className="space-y-3">
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
                {caseData.tags && caseData.tags.length > 0 && (
                  <div>
                    <dt className="text-sm text-gray-500">Tags</dt>
                    <dd className="flex flex-wrap gap-1 mt-1">
                      {caseData.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </dd>
                  </div>
                )}
              </dl>
            </Card>
          </div>
        </div>
      )}

      {activeTab === 'evidence' && (
        <Card>
          <CardHeader title="Evidence" subtitle={`${evidenceData?.length || 0} items`} />
          {!evidenceData || evidenceData.length === 0 ? (
            <p className="text-gray-500 text-sm">No evidence attached</p>
          ) : (
            <div className="space-y-3">
              {evidenceData.map((item: Evidence) => (
                <div
                  key={item.id}
                  className="p-3 border border-gray-200 rounded-lg"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{item.file_name}</p>
                      <p className="text-sm text-gray-500">{item.file_type}</p>
                    </div>
                    <Badge value={item.evidence_type} />
                  </div>
                  {item.description && (
                    <p className="mt-2 text-sm text-gray-600">{item.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
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
                  className="p-3 border border-gray-200 rounded-lg"
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
                    <p className="font-medium text-gray-900">{event.title}</p>
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
    </div>
  );
}

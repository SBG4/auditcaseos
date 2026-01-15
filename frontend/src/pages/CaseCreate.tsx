import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { casesApi } from '../services/api';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import type { CaseStatus, CaseType, Severity } from '../types';

export default function CaseCreate() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    title: '',
    summary: '',
    description: '',
    scope_code: 'GEN',
    case_type: 'POLICY' as CaseType,
    severity: 'MEDIUM' as Severity,
    status: 'OPEN' as CaseStatus,
    tags: '',
    metadata: '',
  });

  const [error, setError] = useState('');

  const createCase = useMutation({
    mutationFn: casesApi.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      navigate(`/cases/${data.id}`);
    },
    onError: (err: unknown) => {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create case';
      setError(errorMessage);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (formData.title.length < 5) {
      setError('Title must be at least 5 characters');
      return;
    }
    if (formData.summary.length < 10) {
      setError('Summary must be at least 10 characters');
      return;
    }

    // Parse tags - only include if not empty
    const tags = formData.tags.trim()
      ? formData.tags.split(',').map((t) => t.trim()).filter(Boolean)
      : undefined;

    // Parse metadata JSON
    let metadata: Record<string, unknown> | undefined;
    if (formData.metadata.trim()) {
      try {
        metadata = JSON.parse(formData.metadata);
      } catch {
        setError('Invalid JSON in metadata field');
        return;
      }
    }

    createCase.mutate({
      title: formData.title,
      summary: formData.summary,
      description: formData.description || undefined,
      scope_code: formData.scope_code,
      case_type: formData.case_type,
      severity: formData.severity,
      tags,
      metadata,
    });
  };

  const scopes = [
    { code: 'FIN', name: 'Finance' },
    { code: 'HR', name: 'Human Resources' },
    { code: 'IT', name: 'Information Technology' },
    { code: 'SEC', name: 'Security' },
    { code: 'OPS', name: 'Operations' },
    { code: 'LEG', name: 'Legal' },
    { code: 'PRO', name: 'Procurement' },
    { code: 'MKT', name: 'Marketing' },
    { code: 'RND', name: 'R&D' },
    { code: 'QA', name: 'Quality Assurance' },
    { code: 'GEN', name: 'General' },
  ];

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Create New Case</h1>
        <p className="mt-1 text-sm text-gray-500">
          Fill in the details to create a new audit case
        </p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded-md text-sm">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="title" className="label">
              Title * <span className="text-gray-400 font-normal">(min 5 characters)</span>
            </label>
            <input
              id="title"
              type="text"
              required
              minLength={5}
              value={formData.title}
              onChange={(e) =>
                setFormData({ ...formData, title: e.target.value })
              }
              className="input mt-1"
              placeholder="Enter case title"
            />
          </div>

          <div>
            <label htmlFor="summary" className="label">
              Summary * <span className="text-gray-400 font-normal">(min 10 characters)</span>
            </label>
            <input
              id="summary"
              type="text"
              required
              minLength={10}
              value={formData.summary}
              onChange={(e) =>
                setFormData({ ...formData, summary: e.target.value })
              }
              className="input mt-1"
              placeholder="Brief summary of the case"
            />
          </div>

          <div>
            <label htmlFor="description" className="label">
              Description
            </label>
            <textarea
              id="description"
              rows={4}
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              className="input mt-1"
              placeholder="Detailed case description"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="scope_code" className="label">
                Scope/Department *
              </label>
              <select
                id="scope_code"
                required
                value={formData.scope_code}
                onChange={(e) =>
                  setFormData({ ...formData, scope_code: e.target.value })
                }
                className="input mt-1"
              >
                {scopes.map((scope) => (
                  <option key={scope.code} value={scope.code}>
                    {scope.code} - {scope.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="case_type" className="label">
                Case Type *
              </label>
              <select
                id="case_type"
                required
                value={formData.case_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    case_type: e.target.value as CaseType,
                  })
                }
                className="input mt-1"
              >
                <option value="USB">USB/Removable Media</option>
                <option value="EMAIL">Email Incident</option>
                <option value="WEB">Web/Internet</option>
                <option value="POLICY">Policy Violation</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="severity" className="label">
                Severity
              </label>
              <select
                id="severity"
                value={formData.severity}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    severity: e.target.value as Severity,
                  })
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

            <div>
              <label htmlFor="status" className="label">
                Status
              </label>
              <select
                id="status"
                value={formData.status}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    status: e.target.value as CaseStatus,
                  })
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
          </div>

          <div>
            <label htmlFor="tags" className="label">
              Tags
            </label>
            <input
              id="tags"
              type="text"
              value={formData.tags}
              onChange={(e) =>
                setFormData({ ...formData, tags: e.target.value })
              }
              className="input mt-1"
              placeholder="e.g., confidential, urgent, finance"
            />
            <p className="mt-1 text-xs text-gray-500">
              Separate multiple tags with commas
            </p>
          </div>

          <div>
            <label htmlFor="metadata" className="label">
              Custom Metadata (JSON)
            </label>
            <textarea
              id="metadata"
              rows={3}
              value={formData.metadata}
              onChange={(e) =>
                setFormData({ ...formData, metadata: e.target.value })
              }
              className="input mt-1 font-mono text-sm"
              placeholder='{"custom_field": "value", "priority": 1}'
            />
            <p className="mt-1 text-xs text-gray-500">
              Optional JSON object for custom fields
            </p>
          </div>

          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate('/cases')}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={createCase.isPending}>
              Create Case
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { PlusIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { casesApi } from '../services/api';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Card from '../components/common/Card';
import type { Case, CaseStatus, Severity } from '../types';
import { format } from 'date-fns';

export default function CaseList() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<CaseStatus | ''>('');
  const [severityFilter, setSeverityFilter] = useState<Severity | ''>('');

  const { data, isLoading } = useQuery({
    queryKey: ['cases', { status: statusFilter, severity: severityFilter }],
    queryFn: () =>
      casesApi.list({
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        page_size: 100,
      }),
  });

  const cases = data?.items || [];
  const filteredCases = cases.filter((c: Case) =>
    c.title.toLowerCase().includes(search.toLowerCase()) ||
    c.case_number.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cases</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage and track all audit cases
          </p>
        </div>
        <Link to="/cases/new">
          <Button>
            <PlusIcon className="w-5 h-5 mr-2" />
            New Case
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card padding="sm">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search cases..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>
          <div className="flex gap-4">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as CaseStatus | '')}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">All Status</option>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="CLOSED">Closed</option>
              <option value="ARCHIVED">Archived</option>
            </select>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as Severity | '')}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">All Severity</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
              <option value="INFO">Info</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Cases Table */}
      <Card padding="none">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No cases found</p>
            <Link to="/cases/new" className="mt-4 inline-block">
              <Button>Create your first case</Button>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Case
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Severity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Updated
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredCases.map((caseItem: Case) => (
                  <tr
                    key={caseItem.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => window.location.href = `/cases/${caseItem.id}`}
                  >
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {caseItem.title}
                        </p>
                        <p className="text-sm text-gray-500">
                          {caseItem.case_number}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant="status" value={caseItem.status} />
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant="severity" value={caseItem.severity} />
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {format(new Date(caseItem.created_at), 'MMM d, yyyy')}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {format(new Date(caseItem.updated_at), 'MMM d, yyyy')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  FolderOpenIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  UserGroupIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { analyticsApi } from '../services/api';
import Card, { CardHeader } from '../components/common/Card';

// Chart colors
const COLORS = {
  primary: '#3B82F6',
  success: '#10B981',
  warning: '#F59E0B',
  danger: '#EF4444',
  info: '#06B6D4',
  gray: '#6B7280',
  purple: '#8B5CF6',
  pink: '#EC4899',
};

const STATUS_COLORS: Record<string, string> = {
  OPEN: COLORS.primary,
  IN_PROGRESS: COLORS.warning,
  PENDING_REVIEW: COLORS.info,
  CLOSED: COLORS.success,
  ARCHIVED: COLORS.gray,
};

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: COLORS.danger,
  HIGH: COLORS.warning,
  MEDIUM: COLORS.info,
  LOW: COLORS.success,
  INFO: COLORS.gray,
};

const TYPE_COLORS = [COLORS.primary, COLORS.success, COLORS.warning, COLORS.purple];

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  subtitle?: string;
}

function StatCard({ title, value, icon: Icon, color, subtitle }: StatCardProps) {
  return (
    <Card>
      <div className="flex items-center">
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
          {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
        </div>
      </div>
    </Card>
  );
}

function ChartSkeleton() {
  return (
    <div className="animate-pulse flex items-center justify-center h-64 bg-gray-100 rounded-lg">
      <ChartBarIcon className="w-12 h-12 text-gray-300" />
    </div>
  );
}

export default function Analytics() {
  const [days, setDays] = useState(30);

  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', days],
    queryFn: () => analyticsApi.getFullAnalytics(days),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
            <p className="mt-1 text-sm text-gray-500">Loading analytics data...</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse bg-gray-100 h-24 rounded-lg"></div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Error loading analytics</h3>
        <p className="mt-1 text-sm text-gray-500">
          {error instanceof Error ? error.message : 'Failed to load analytics data'}
        </p>
      </div>
    );
  }

  const { overview, case_stats, trends, evidence_findings, entities, user_activity } = data;

  // Format date for chart display
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };

  const trendsData = trends.data.map((d) => ({
    ...d,
    date: formatDate(d.date),
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            Visual insights into your audit cases and activity
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <label htmlFor="period" className="text-sm font-medium text-gray-700">
            Period:
          </label>
          <select
            id="period"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Cases"
          value={overview.total_cases}
          icon={FolderOpenIcon}
          color="bg-primary-500"
        />
        <StatCard
          title="Open Cases"
          value={overview.open_cases}
          icon={ClockIcon}
          color="bg-yellow-500"
          subtitle={`${overview.in_progress_cases} in progress`}
        />
        <StatCard
          title="Critical Cases"
          value={overview.critical_cases}
          icon={ExclamationTriangleIcon}
          color="bg-red-500"
          subtitle={`${overview.high_severity_cases} high severity`}
        />
        <StatCard
          title="Avg Resolution"
          value={overview.avg_resolution_days ? `${overview.avg_resolution_days}d` : 'N/A'}
          icon={CheckCircleIcon}
          color="bg-green-500"
          subtitle={`${overview.closed_cases} cases closed`}
        />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          title="Total Evidence"
          value={overview.total_evidence}
          icon={DocumentTextIcon}
          color="bg-indigo-500"
        />
        <StatCard
          title="Total Findings"
          value={overview.total_findings}
          icon={MagnifyingGlassIcon}
          color="bg-purple-500"
        />
        <StatCard
          title="Extracted Entities"
          value={overview.total_entities}
          icon={UserGroupIcon}
          color="bg-pink-500"
        />
      </div>

      {/* Charts Row 1: Trends + Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Case Trends */}
        <Card>
          <CardHeader title="Case Trends" subtitle={`Last ${days} days`} />
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendsData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="created"
                  stroke={COLORS.primary}
                  strokeWidth={2}
                  name="Created"
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="closed"
                  stroke={COLORS.success}
                  strokeWidth={2}
                  name="Closed"
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 text-center text-sm text-gray-500">
            {trends.total_created} created, {trends.total_closed} closed
          </div>
        </Card>

        {/* Status Distribution */}
        <Card>
          <CardHeader title="Cases by Status" subtitle={`${case_stats.total} total cases`} />
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={case_stats.by_status as unknown as Record<string, unknown>[]}
                  dataKey="count"
                  nameKey="status"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                  labelLine={{ stroke: '#666', strokeWidth: 1 }}
                >
                  {case_stats.by_status.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={STATUS_COLORS[entry.status] || COLORS.gray}
                    />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [`${value} cases`, name]} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Charts Row 2: Severity + Case Types */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Severity Distribution */}
        <Card>
          <CardHeader title="Cases by Severity" />
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={case_stats.by_severity} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis dataKey="severity" type="category" tick={{ fontSize: 12 }} width={80} />
                <Tooltip formatter={(value) => [`${value} cases`]} />
                <Bar dataKey="count" name="Cases">
                  {case_stats.by_severity.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={SEVERITY_COLORS[entry.severity] || COLORS.gray}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Case Types */}
        <Card>
          <CardHeader title="Cases by Type" />
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={case_stats.by_type}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="type" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => [`${value} cases`]} />
                <Bar dataKey="count" name="Cases">
                  {case_stats.by_type.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={TYPE_COLORS[index % TYPE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Charts Row 3: Scope + Evidence */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cases by Scope */}
        <Card>
          <CardHeader title="Cases by Department" />
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={case_stats.by_scope.slice(0, 8)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis
                  dataKey="scope_code"
                  type="category"
                  tick={{ fontSize: 12 }}
                  width={50}
                />
                <Tooltip
                  formatter={(value, _, props) => [
                    `${value} cases`,
                    props.payload?.scope_name || '',
                  ]}
                />
                <Bar dataKey="count" fill={COLORS.primary} name="Cases" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Evidence by Type */}
        <Card>
          <CardHeader
            title="Evidence by Type"
            subtitle={`${evidence_findings.total_evidence} total files`}
          />
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={evidence_findings.evidence_by_type as unknown as Record<string, unknown>[]}
                  dataKey="count"
                  nameKey="type"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                  labelLine={{ stroke: '#666', strokeWidth: 1 }}
                >
                  {evidence_findings.evidence_by_type.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={TYPE_COLORS[index % TYPE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [`${value} files`, name]} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Charts Row 4: Findings + Entities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Findings by Severity */}
        <Card>
          <CardHeader
            title="Findings by Severity"
            subtitle={`${evidence_findings.total_findings} total findings`}
          />
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={evidence_findings.findings_by_severity}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="severity" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => [`${value} findings`]} />
                <Bar dataKey="count" name="Findings">
                  {evidence_findings.findings_by_severity.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={SEVERITY_COLORS[entry.severity] || COLORS.gray}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Entity Types */}
        <Card>
          <CardHeader
            title="Extracted Entity Types"
            subtitle={`${entities.total_entities} total entities`}
          />
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={entities.by_type} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis dataKey="entity_type" type="category" tick={{ fontSize: 12 }} width={100} />
                <Tooltip
                  formatter={(value, _, props) => [
                    `${value} total (${props.payload?.unique_values || 0} unique)`,
                  ]}
                />
                <Bar dataKey="count" fill={COLORS.purple} name="Count" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* User Activity Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity by Action */}
        <Card>
          <CardHeader
            title="User Activity"
            subtitle={`${user_activity.total_actions} actions in last ${user_activity.period_days} days`}
          />
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={user_activity.by_action.slice(0, 8)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="action" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" height={80} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => [`${value} actions`]} />
                <Bar dataKey="count" fill={COLORS.info} name="Actions" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Top Users */}
        <Card>
          <CardHeader title="Top Active Users" subtitle={`Last ${user_activity.period_days} days`} />
          <div className="mt-4 space-y-3">
            {user_activity.top_users.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">No user activity recorded</p>
            ) : (
              user_activity.top_users.slice(0, 5).map((user, index) => (
                <div
                  key={user.user_id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                      <span className="text-sm font-medium text-primary-700">{index + 1}</span>
                    </div>
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-900">{user.user_email}</p>
                      <p className="text-xs text-gray-500">
                        Last active: {new Date(user.last_activity).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-900">{user.action_count}</p>
                    <p className="text-xs text-gray-500">actions</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      {/* Top Entities Table */}
      {entities.top_entities.length > 0 && (
        <Card>
          <CardHeader title="Top Extracted Entities" subtitle="Most frequently occurring entities across all cases" />
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Value
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Occurrences
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Cases
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {entities.top_entities.slice(0, 10).map((entity, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-mono text-gray-900">{entity.value}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {entity.entity_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 text-right">
                      {entity.occurrence_count}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 text-right">{entity.case_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

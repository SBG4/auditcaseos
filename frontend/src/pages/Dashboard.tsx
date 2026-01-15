import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  FolderOpenIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { casesApi } from '../services/api';
import Card, { CardHeader } from '../components/common/Card';
import Badge from '../components/common/Badge';
import type { Case } from '../types';

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

function StatCard({ title, value, icon: Icon, color }: StatCardProps) {
  return (
    <Card>
      <div className="flex items-center">
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
        </div>
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const { data: cases, isLoading } = useQuery({
    queryKey: ['cases'],
    queryFn: () => casesApi.list({ limit: 100 }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const caseList = cases?.items || [];
  const stats = {
    total: caseList.length,
    open: caseList.filter((c: Case) => c.status === 'OPEN').length,
    inProgress: caseList.filter((c: Case) => c.status === 'IN_PROGRESS').length,
    closed: caseList.filter((c: Case) => c.status === 'CLOSED').length,
  };

  const recentCases = caseList.slice(0, 5);
  const criticalCases = caseList.filter(
    (c: Case) => c.severity === 'CRITICAL' && c.status !== 'CLOSED'
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your audit cases and activity
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Cases"
          value={stats.total}
          icon={FolderOpenIcon}
          color="bg-primary-500"
        />
        <StatCard
          title="Open"
          value={stats.open}
          icon={ExclamationTriangleIcon}
          color="bg-blue-500"
        />
        <StatCard
          title="In Progress"
          value={stats.inProgress}
          icon={ClockIcon}
          color="bg-yellow-500"
        />
        <StatCard
          title="Closed"
          value={stats.closed}
          icon={CheckCircleIcon}
          color="bg-green-500"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Cases */}
        <Card>
          <CardHeader
            title="Recent Cases"
            action={
              <Link
                to="/cases"
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                View all
              </Link>
            }
          />
          {recentCases.length === 0 ? (
            <p className="text-sm text-gray-500">No cases yet</p>
          ) : (
            <div className="space-y-3">
              {recentCases.map((caseItem: Case) => (
                <Link
                  key={caseItem.id}
                  to={`/cases/${caseItem.id}`}
                  className="block p-3 -mx-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {caseItem.title}
                      </p>
                      <p className="text-sm text-gray-500">
                        {caseItem.case_number}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <Badge variant="status" value={caseItem.status} />
                      <Badge variant="severity" value={caseItem.severity} />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>

        {/* Critical Cases */}
        <Card>
          <CardHeader title="Critical Cases" subtitle="Requiring immediate attention" />
          {criticalCases.length === 0 ? (
            <p className="text-sm text-gray-500">No critical cases</p>
          ) : (
            <div className="space-y-3">
              {criticalCases.map((caseItem: Case) => (
                <Link
                  key={caseItem.id}
                  to={`/cases/${caseItem.id}`}
                  className="block p-3 -mx-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {caseItem.title}
                      </p>
                      <p className="text-sm text-gray-500">
                        {caseItem.case_number}
                      </p>
                    </div>
                    <Badge variant="status" value={caseItem.status} />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

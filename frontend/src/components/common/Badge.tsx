import type { CaseStatus, Severity } from '../../types';

interface BadgeProps {
  variant?: 'default' | 'status' | 'severity';
  value: string;
  size?: 'sm' | 'md';
}

const statusColors: Record<CaseStatus, string> = {
  OPEN: 'bg-blue-100 text-blue-800',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
  PENDING_REVIEW: 'bg-purple-100 text-purple-800',
  CLOSED: 'bg-green-100 text-green-800',
  ARCHIVED: 'bg-gray-100 text-gray-800',
};

const severityColors: Record<Severity, string> = {
  CRITICAL: 'bg-red-100 text-red-800',
  HIGH: 'bg-orange-100 text-orange-800',
  MEDIUM: 'bg-yellow-100 text-yellow-800',
  LOW: 'bg-green-100 text-green-800',
  INFO: 'bg-blue-100 text-blue-800',
};

export default function Badge({ variant = 'default', value, size = 'sm' }: BadgeProps) {
  let colorClass = 'bg-gray-100 text-gray-800';

  if (variant === 'status' && value in statusColors) {
    colorClass = statusColors[value as CaseStatus];
  } else if (variant === 'severity' && value in severityColors) {
    colorClass = severityColors[value as Severity];
  }

  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm';

  return (
    <span
      className={`
        inline-flex items-center font-medium rounded-full
        ${colorClass}
        ${sizeClass}
      `}
    >
      {value.replace('_', ' ')}
    </span>
  );
}

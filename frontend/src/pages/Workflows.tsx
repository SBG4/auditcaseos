import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BoltIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  PauseIcon,
  ClockIcon,
  ArrowPathIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import { workflowsApi } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import Button from '../components/common/Button';
import Card, { CardHeader } from '../components/common/Card';
import type {
  WorkflowRule,
  WorkflowRuleCreate,
  TriggerType,
  ActionType,
  WorkflowHistory,
} from '../types';

const triggerTypeLabels: Record<TriggerType, string> = {
  STATUS_CHANGE: 'Status Change',
  TIME_BASED: 'Time Based',
  EVENT: 'Event',
  CONDITION: 'Condition',
};

const actionTypeLabels: Record<ActionType, string> = {
  CHANGE_STATUS: 'Change Status',
  ASSIGN_USER: 'Assign User',
  ADD_TAG: 'Add Tag',
  SEND_NOTIFICATION: 'Send Notification',
  CREATE_TIMELINE: 'Create Timeline Entry',
};

const triggerTypeColors: Record<TriggerType, string> = {
  STATUS_CHANGE: 'bg-blue-100 text-blue-800',
  TIME_BASED: 'bg-purple-100 text-purple-800',
  EVENT: 'bg-green-100 text-green-800',
  CONDITION: 'bg-orange-100 text-orange-800',
};

export default function Workflows() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [showHistory, setShowHistory] = useState(false);
  const [expandedRule, setExpandedRule] = useState<string | null>(null);

  // Access check
  if (user?.role !== 'admin') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="text-center p-8">
          <BoltIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-gray-600">You need admin privileges to manage workflows.</p>
        </Card>
      </div>
    );
  }

  const { data: rulesData, isLoading } = useQuery({
    queryKey: ['workflow-rules'],
    queryFn: () => workflowsApi.listRules({ page: 1, page_size: 50 }),
  });

  const { data: historyData } = useQuery({
    queryKey: ['workflow-history'],
    queryFn: () => workflowsApi.getAllHistory({ page: 1, page_size: 20 }),
    enabled: showHistory,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      workflowsApi.toggleRule(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-rules'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => workflowsApi.deleteRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-rules'] });
    },
  });

  const rules = rulesData?.items || [];
  const history = historyData?.items || [];

  const enabledCount = rules.filter((r) => r.is_enabled).length;
  const disabledCount = rules.filter((r) => !r.is_enabled).length;

  const handleToggle = (rule: WorkflowRule) => {
    toggleMutation.mutate({ id: rule.id, enabled: !rule.is_enabled });
  };

  const handleDelete = (rule: WorkflowRule) => {
    if (confirm(`Are you sure you want to delete the workflow rule "${rule.name}"?`)) {
      deleteMutation.mutate(rule.id);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Workflow Automation</h1>
          <p className="mt-1 text-sm text-gray-500">
            Configure automated rules to streamline case management
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowHistory(!showHistory)}>
            <ClockIcon className="w-5 h-5 mr-2" />
            {showHistory ? 'Hide History' : 'Show History'}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center">
            <BoltIcon className="w-10 h-10 text-primary-600" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">Total Rules</p>
              <p className="text-2xl font-bold text-gray-900">{rules.length}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center">
            <PlayIcon className="w-10 h-10 text-green-600" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">Active Rules</p>
              <p className="text-2xl font-bold text-gray-900">{enabledCount}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center">
            <PauseIcon className="w-10 h-10 text-gray-400" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">Disabled Rules</p>
              <p className="text-2xl font-bold text-gray-900">{disabledCount}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center">
            <ArrowPathIcon className="w-10 h-10 text-blue-600" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">Recent Executions</p>
              <p className="text-2xl font-bold text-gray-900">{historyData?.total || '-'}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* History Section */}
      {showHistory && (
        <Card>
          <CardHeader
            title="Execution History"
            subtitle={`Last ${history.length} executions`}
          />
          {history.length === 0 ? (
            <div className="py-8 text-center text-gray-500">
              <ClockIcon className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>No workflow executions yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Rule
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Case
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Trigger
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Executed At
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {history.map((h: WorkflowHistory) => (
                    <tr key={h.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {h.rule_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {h.case_id_str}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            triggerTypeColors[h.trigger_type]
                          }`}
                        >
                          {triggerTypeLabels[h.trigger_type]}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {h.success ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                            Success
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                            Failed
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {formatDate(h.executed_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Rules List */}
      <Card>
        <CardHeader
          title="Workflow Rules"
          subtitle={`${rules.length} rules configured`}
        />
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : rules.length === 0 ? (
          <div className="text-center py-12">
            <BoltIcon className="w-12 h-12 text-gray-300 mx-auto" />
            <p className="mt-4 text-gray-500">No workflow rules configured</p>
            <p className="text-sm text-gray-400 mt-2">
              Workflow rules can be created via the API
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {rules.map((rule) => (
              <div key={rule.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    {/* Expand/collapse */}
                    <button
                      onClick={() =>
                        setExpandedRule(expandedRule === rule.id ? null : rule.id)
                      }
                      className="p-1 text-gray-400 hover:text-gray-600"
                    >
                      {expandedRule === rule.id ? (
                        <ChevronDownIcon className="w-5 h-5" />
                      ) : (
                        <ChevronRightIcon className="w-5 h-5" />
                      )}
                    </button>

                    {/* Status indicator */}
                    <div
                      className={`w-3 h-3 rounded-full ${
                        rule.is_enabled ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                    />

                    {/* Rule info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900">{rule.name}</h3>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            triggerTypeColors[rule.trigger_type]
                          }`}
                        >
                          {triggerTypeLabels[rule.trigger_type]}
                        </span>
                      </div>
                      {rule.description && (
                        <p className="text-sm text-gray-500 mt-1">{rule.description}</p>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggle(rule)}
                      className={`p-2 rounded hover:bg-gray-100 ${
                        rule.is_enabled
                          ? 'text-green-600 hover:text-green-700'
                          : 'text-gray-400 hover:text-gray-600'
                      }`}
                      title={rule.is_enabled ? 'Disable rule' : 'Enable rule'}
                      disabled={toggleMutation.isPending}
                    >
                      {rule.is_enabled ? (
                        <PauseIcon className="w-5 h-5" />
                      ) : (
                        <PlayIcon className="w-5 h-5" />
                      )}
                    </button>
                    <button
                      onClick={() => handleDelete(rule)}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                      title="Delete rule"
                      disabled={deleteMutation.isPending}
                    >
                      <TrashIcon className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Expanded details */}
                {expandedRule === rule.id && (
                  <div className="mt-4 ml-12 p-4 bg-gray-50 rounded-lg">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Priority</p>
                        <p className="font-medium">{rule.priority}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Created</p>
                        <p className="font-medium">{formatDate(rule.created_at)}</p>
                      </div>
                      {rule.scope_codes && rule.scope_codes.length > 0 && (
                        <div>
                          <p className="text-gray-500">Scope Filter</p>
                          <p className="font-medium">{rule.scope_codes.join(', ')}</p>
                        </div>
                      )}
                      {rule.case_types && rule.case_types.length > 0 && (
                        <div>
                          <p className="text-gray-500">Case Type Filter</p>
                          <p className="font-medium">{rule.case_types.join(', ')}</p>
                        </div>
                      )}
                    </div>

                    {/* Trigger config */}
                    <div className="mt-4">
                      <p className="text-sm text-gray-500 mb-2">Trigger Configuration</p>
                      <pre className="text-xs bg-white p-2 rounded border overflow-x-auto">
                        {JSON.stringify(rule.trigger_config, null, 2)}
                      </pre>
                    </div>

                    {/* Actions */}
                    {rule.actions && rule.actions.length > 0 && (
                      <div className="mt-4">
                        <p className="text-sm text-gray-500 mb-2">
                          Actions ({rule.actions.length})
                        </p>
                        <ul className="space-y-2">
                          {rule.actions.map((action, idx) => (
                            <li
                              key={action.id}
                              className="flex items-center gap-2 text-sm bg-white p-2 rounded border"
                            >
                              <span className="text-gray-400">{idx + 1}.</span>
                              <span className="font-medium">
                                {actionTypeLabels[action.action_type]}
                              </span>
                              <span className="text-gray-400">-</span>
                              <span className="text-gray-600 text-xs">
                                {JSON.stringify(action.action_config)}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Info card */}
      <Card className="p-4 bg-blue-50 border-blue-200">
        <div className="flex gap-4">
          <BoltIcon className="w-6 h-6 text-blue-600 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-blue-900">Creating Workflow Rules</h4>
            <p className="text-sm text-blue-700 mt-1">
              Workflow rules can be created via the API. Use POST /api/v1/workflows/rules
              to create a new rule with triggers and actions. Rules can automate case
              status changes, user assignments, notifications, and more.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}

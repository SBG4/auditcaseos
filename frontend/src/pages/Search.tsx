import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  TagIcon,
  CalendarDaysIcon,
  PaperClipIcon,
} from '@heroicons/react/24/outline';
import { searchApi } from '../services/api';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import type { SearchEntityType, SearchMode, SearchResultItem } from '../types';
import { format } from 'date-fns';

const ENTITY_TYPES: { value: SearchEntityType; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'case', label: 'Cases' },
  { value: 'evidence', label: 'Evidence' },
  { value: 'finding', label: 'Findings' },
  { value: 'entity', label: 'Entities' },
  { value: 'timeline', label: 'Timeline' },
];

const SEARCH_MODES: { value: SearchMode; label: string; description: string }[] = [
  { value: 'hybrid', label: 'Hybrid', description: 'Combined keyword and semantic' },
  { value: 'keyword', label: 'Keyword', description: 'Exact text matching' },
  { value: 'semantic', label: 'Semantic', description: 'AI-powered similarity' },
];

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const initialEntityTypes = searchParams.get('entity_types')?.split(',') as SearchEntityType[] || ['all'];
  const initialMode = (searchParams.get('mode') as SearchMode) || 'hybrid';

  const [query, setQuery] = useState(initialQuery);
  const [entityTypes, setEntityTypes] = useState<SearchEntityType[]>(initialEntityTypes);
  const [mode, setMode] = useState<SearchMode>(initialMode);
  const [showFilters, setShowFilters] = useState(false);
  const [page, setPage] = useState(1);

  // Update state when URL params change
  useEffect(() => {
    const q = searchParams.get('q') || '';
    setQuery(q);
    if (searchParams.get('entity_types')) {
      setEntityTypes(searchParams.get('entity_types')!.split(',') as SearchEntityType[]);
    }
    if (searchParams.get('mode')) {
      setMode(searchParams.get('mode') as SearchMode);
    }
  }, [searchParams]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['search', query, entityTypes, mode, page],
    queryFn: () =>
      searchApi.search({
        q: query,
        entity_types: entityTypes.includes('all') ? undefined : entityTypes,
        mode,
        page,
        page_size: 20,
      }),
    enabled: query.length >= 2,
    keepPreviousData: true,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      const params = new URLSearchParams();
      params.set('q', query.trim());
      if (!entityTypes.includes('all')) {
        params.set('entity_types', entityTypes.join(','));
      }
      if (mode !== 'hybrid') {
        params.set('mode', mode);
      }
      setSearchParams(params);
      setPage(1);
    }
  };

  const toggleEntityType = (type: SearchEntityType) => {
    if (type === 'all') {
      setEntityTypes(['all']);
    } else {
      let newTypes = entityTypes.filter((t) => t !== 'all');
      if (newTypes.includes(type)) {
        newTypes = newTypes.filter((t) => t !== type);
      } else {
        newTypes.push(type);
      }
      if (newTypes.length === 0) {
        newTypes = ['all'];
      }
      setEntityTypes(newTypes);
    }
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'case':
        return <ClipboardDocumentListIcon className="w-5 h-5" />;
      case 'evidence':
        return <PaperClipIcon className="w-5 h-5" />;
      case 'finding':
        return <DocumentTextIcon className="w-5 h-5" />;
      case 'entity':
        return <TagIcon className="w-5 h-5" />;
      case 'timeline':
        return <CalendarDaysIcon className="w-5 h-5" />;
      default:
        return <DocumentTextIcon className="w-5 h-5" />;
    }
  };

  const getEntityColor = (type: string): 'primary' | 'success' | 'warning' | 'danger' | 'gray' => {
    switch (type) {
      case 'case':
        return 'primary';
      case 'evidence':
        return 'success';
      case 'finding':
        return 'warning';
      case 'entity':
        return 'danger';
      case 'timeline':
        return 'gray';
      default:
        return 'gray';
    }
  };

  const getResultLink = (result: SearchResultItem): string => {
    switch (result.entity_type) {
      case 'case':
        return `/cases/${result.id}`;
      case 'evidence':
        return result.case_uuid ? `/cases/${result.case_uuid}#evidence-${result.id}` : '#';
      case 'finding':
        return result.case_uuid ? `/cases/${result.case_uuid}#finding-${result.id}` : '#';
      case 'entity':
        return result.case_uuid ? `/cases/${result.case_uuid}#entities` : '#';
      case 'timeline':
        return result.case_uuid ? `/cases/${result.case_uuid}#timeline` : '#';
      default:
        return '#';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Search</h1>
        <p className="mt-1 text-sm text-gray-500">
          Search across all cases, evidence, findings, and more
        </p>
      </div>

      {/* Search Form */}
      <Card>
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter search query..."
                className="w-full pl-10 pr-4 py-3 text-lg border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <button
              type="submit"
              disabled={query.trim().length < 2}
              className="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Search
            </button>
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-3 border rounded-lg transition-colors ${
                showFilters ? 'bg-gray-100 border-gray-400' : 'border-gray-300 hover:bg-gray-50'
              }`}
            >
              <FunnelIcon className="w-5 h-5 text-gray-600" />
            </button>
          </div>

          {/* Filters */}
          {showFilters && (
            <div className="pt-4 border-t border-gray-200 space-y-4">
              {/* Entity Type Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Search in
                </label>
                <div className="flex flex-wrap gap-2">
                  {ENTITY_TYPES.map((type) => (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => toggleEntityType(type.value)}
                      className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                        entityTypes.includes(type.value)
                          ? 'bg-primary-100 border-primary-300 text-primary-700'
                          : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {type.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Search Mode */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Search mode
                </label>
                <div className="flex gap-4">
                  {SEARCH_MODES.map((m) => (
                    <label key={m.value} className="flex items-start gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="mode"
                        value={m.value}
                        checked={mode === m.value}
                        onChange={(e) => setMode(e.target.value as SearchMode)}
                        className="mt-1"
                      />
                      <div>
                        <span className="text-sm font-medium text-gray-900">{m.label}</span>
                        <p className="text-xs text-gray-500">{m.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}
        </form>
      </Card>

      {/* Results */}
      {query.length >= 2 && (
        <>
          {/* Results Summary */}
          {data && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Found <span className="font-semibold">{data.total}</span> results
                {data.search_time_ms && (
                  <span className="text-gray-400"> in {data.search_time_ms.toFixed(0)}ms</span>
                )}
              </div>
              {/* Entity type counts */}
              <div className="flex gap-2">
                {Object.entries(data.entity_type_counts || {}).map(([type, count]) => (
                  <span
                    key={type}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded"
                  >
                    {type}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Results List */}
          <Card padding="none">
            {isLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
              </div>
            ) : !data?.items?.length ? (
              <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                <MagnifyingGlassIcon className="w-12 h-12 mb-4 text-gray-300" />
                <p className="text-lg font-medium">No results found</p>
                <p className="text-sm">Try different keywords or filters</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {data.items.map((result) => (
                  <Link
                    key={`${result.entity_type}-${result.id}`}
                    to={getResultLink(result)}
                    className="block p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start gap-4">
                      <div
                        className={`p-2 rounded-lg bg-${getEntityColor(result.entity_type)}-100 text-${getEntityColor(result.entity_type)}-600`}
                      >
                        {getEntityIcon(result.entity_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-semibold text-gray-900 truncate">
                            {result.title}
                          </h3>
                          <Badge variant={getEntityColor(result.entity_type)} size="sm">
                            {result.entity_type}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 line-clamp-2">{result.snippet}</p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                          {result.case_id && (
                            <span>Case: {result.case_id}</span>
                          )}
                          <span>
                            {format(new Date(result.created_at), 'MMM d, yyyy')}
                          </span>
                          {result.combined_score > 0 && (
                            <span>Score: {(result.combined_score * 100).toFixed(0)}%</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </Card>

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1 || isFetching}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-sm text-gray-600">
                Page {page} of {data.total_pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={page === data.total_pages || isFetching}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {/* Empty state when no query */}
      {query.length < 2 && (
        <Card>
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <MagnifyingGlassIcon className="w-16 h-16 mb-4 text-gray-300" />
            <p className="text-lg font-medium">Start searching</p>
            <p className="text-sm mt-1">Enter at least 2 characters to search</p>
            <div className="mt-6 grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
              {ENTITY_TYPES.filter((t) => t.value !== 'all').map((type) => (
                <div key={type.value} className="p-3 bg-gray-50 rounded-lg">
                  <div className="text-2xl mb-1">
                    {type.value === 'case' && '📁'}
                    {type.value === 'evidence' && '📎'}
                    {type.value === 'finding' && '🔍'}
                    {type.value === 'entity' && '🏷️'}
                    {type.value === 'timeline' && '📅'}
                  </div>
                  <span className="text-xs text-gray-600">{type.label}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

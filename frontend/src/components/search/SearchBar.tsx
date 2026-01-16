import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { searchApi } from '../../services/api';
import { useDebounce } from '../../hooks/useDebounce';
import type { SearchSuggestion } from '../../types';

interface SearchBarProps {
  className?: string;
  placeholder?: string;
}

export default function SearchBar({ className = '', placeholder = 'Search cases, evidence, findings...' }: SearchBarProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const debouncedQuery = useDebounce(query, 300);

  // Fetch suggestions
  const { data: suggestions } = useQuery({
    queryKey: ['searchSuggestions', debouncedQuery],
    queryFn: () => searchApi.suggest(debouncedQuery, 8),
    enabled: debouncedQuery.length >= 2,
    staleTime: 30000,
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
      setIsOpen(false);
    }
  };

  const handleSuggestionClick = (suggestion: SearchSuggestion) => {
    if (suggestion.type === 'entity') {
      navigate(`/search?q=${encodeURIComponent(suggestion.value)}&entity_types=${suggestion.entity_type || 'all'}`);
    } else {
      navigate(`/search?q=${encodeURIComponent(suggestion.value)}`);
    }
    setQuery('');
    setIsOpen(false);
  };

  const handleClear = () => {
    setQuery('');
    inputRef.current?.focus();
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'case':
        return '📁';
      case 'evidence':
        return '📎';
      case 'finding':
        return '🔍';
      case 'entity':
        return '🏷️';
      case 'timeline':
        return '📅';
      default:
        return '📄';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'case':
        return 'Case';
      case 'evidence':
        return 'Evidence';
      case 'finding':
        return 'Finding';
      case 'entity':
        return 'Entity';
      case 'timeline':
        return 'Timeline';
      case 'recent':
        return 'Recent';
      default:
        return type;
    }
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder={placeholder}
            className="w-full pl-10 pr-10 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-gray-50 hover:bg-white focus:bg-white transition-colors"
          />
          {query && (
            <button
              type="button"
              onClick={handleClear}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          )}
        </div>
      </form>

      {/* Suggestions dropdown */}
      {isOpen && suggestions?.suggestions && suggestions.suggestions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-80 overflow-y-auto">
          {suggestions.suggestions.map((suggestion, index) => (
            <button
              key={`${suggestion.type}-${suggestion.value}-${index}`}
              type="button"
              onClick={() => handleSuggestionClick(suggestion)}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center gap-3 border-b border-gray-100 last:border-b-0"
            >
              <span className="text-lg">{getTypeIcon(suggestion.entity_type || suggestion.type)}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{suggestion.value}</p>
                <p className="text-xs text-gray-500">{getTypeLabel(suggestion.entity_type || suggestion.type)}</p>
              </div>
            </button>
          ))}
          {query.trim().length >= 2 && (
            <button
              type="button"
              onClick={handleSubmit}
              className="w-full px-4 py-2 text-left bg-gray-50 hover:bg-gray-100 flex items-center gap-3 text-sm text-primary-600 font-medium"
            >
              <MagnifyingGlassIcon className="w-5 h-5" />
              <span>Search for "{query}"</span>
            </button>
          )}
        </div>
      )}

      {/* Show "Search for..." when no suggestions but query exists */}
      {isOpen && query.trim().length >= 2 && (!suggestions?.suggestions || suggestions.suggestions.length === 0) && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg">
          <button
            type="button"
            onClick={handleSubmit}
            className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center gap-3 text-sm text-gray-700"
          >
            <MagnifyingGlassIcon className="w-5 h-5 text-gray-400" />
            <span>Search for "<span className="font-medium">{query}</span>"</span>
          </button>
        </div>
      )}
    </div>
  );
}

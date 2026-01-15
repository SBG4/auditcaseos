import { Link } from 'react-router-dom';
import {
  Bars3Icon,
  BellIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../../hooks/useAuth';

interface HeaderProps {
  onMenuClick: () => void;
}

export default function Header({ onMenuClick }: HeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="flex items-center justify-between h-16 px-4">
        <div className="flex items-center">
          <button
            type="button"
            className="p-2 text-gray-500 rounded-md lg:hidden hover:bg-gray-100"
            onClick={onMenuClick}
          >
            <Bars3Icon className="w-6 h-6" />
          </button>
          <Link to="/" className="flex items-center ml-2 lg:ml-0">
            <span className="text-xl font-bold text-primary-600">AuditCaseOS</span>
          </Link>
        </div>

        <div className="flex items-center gap-4">
          <button className="p-2 text-gray-500 rounded-md hover:bg-gray-100">
            <BellIcon className="w-6 h-6" />
          </button>

          <div className="relative group">
            <button className="flex items-center gap-2 p-2 rounded-md hover:bg-gray-100">
              <UserCircleIcon className="w-6 h-6 text-gray-500" />
              <span className="hidden text-sm font-medium text-gray-700 md:block">
                {user?.full_name || user?.username}
              </span>
            </button>

            <div className="absolute right-0 z-10 hidden w-48 mt-2 bg-white border border-gray-200 rounded-md shadow-lg group-hover:block">
              <div className="py-1">
                <div className="px-4 py-2 text-sm text-gray-500 border-b">
                  {user?.email}
                </div>
                <Link
                  to="/profile"
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Profile
                </Link>
                {user?.role === 'admin' && (
                  <Link
                    to="/admin"
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Admin
                  </Link>
                )}
                <button
                  onClick={logout}
                  className="block w-full px-4 py-2 text-sm text-left text-red-600 hover:bg-gray-100"
                >
                  Sign out
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

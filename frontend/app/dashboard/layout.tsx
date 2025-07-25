"use client";

import { useState, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import {
  ChartBarIcon,
  CogIcon,
  HomeIcon,
  RectangleStackIcon,
  Bars3Icon,
  XMarkIcon,
  BriefcaseIcon,
  ShieldCheckIcon,
  TableCellsIcon,
} from '@heroicons/react/24/outline';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Menu } from '@headlessui/react';
import { ChevronDownIcon } from '@heroicons/react/20/solid';
import { useAuth } from '../contexts/AuthContext';
import PasswordChangeModal from '../../components/PasswordChangeModal';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Trading Bots', href: '/dashboard/create-bot', icon: RectangleStackIcon },
  { name: 'Exchanges', href: '/dashboard/exchanges', icon: BriefcaseIcon },
  { name: 'Manual Trade', href: '/dashboard/manual-trade', icon: CogIcon },
  { name: 'Stop Loss Status', href: '/dashboard/manual-stop-loss-status', icon: ShieldCheckIcon },
  { name: 'Reports', href: '/dashboard/reports', icon: ChartBarIcon },
];

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const { isAdmin, user } = useAuth();

  // Debug print for admin status
  console.log('isAdmin:', isAdmin, 'user:', user);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    router.push('/login');
  };

  return (
    <div>
        {/* Mobile menu */}
        <Transition.Root show={sidebarOpen} as={Fragment}>
          <Dialog as="div" className="relative z-40 md:hidden" onClose={setSidebarOpen}>
            <Transition.Child
              as={Fragment}
              enter="transition-opacity ease-linear duration-300"
              enterFrom="opacity-0"
              enterTo="opacity-100"
              leave="transition-opacity ease-linear duration-300"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <div className="fixed inset-0 bg-gray-600 bg-opacity-75" />
            </Transition.Child>

            <div className="fixed inset-0 z-40 flex">
              <Transition.Child
                as={Fragment}
                enter="transition ease-in-out duration-300 transform"
                enterFrom="-translate-x-full"
                enterTo="translate-x-0"
                leave="transition ease-in-out duration-300 transform"
                leaveFrom="translate-x-0"
                leaveTo="-translate-x-full"
              >
                <Dialog.Panel className="relative flex w-full max-w-xs flex-1 flex-col bg-gray-900 pt-5 pb-4">
                  <Transition.Child
                    as={Fragment}
                    enter="ease-in-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in-out duration-300"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                  >
                    <div className="absolute top-0 right-0 -mr-12 pt-2">
                      <button
                        type="button"
                        className="ml-1 flex h-10 w-10 items-center justify-center rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
                        onClick={() => setSidebarOpen(false)}
                      >
                        <span className="sr-only">Close sidebar</span>
                        <XMarkIcon className="h-6 w-6 text-white" aria-hidden="true" />
                      </button>
                    </div>
                  </Transition.Child>
                  <div className="flex flex-shrink-0 items-center px-4">
                      <ChartBarIcon className="h-8 w-8 text-blue-500 mr-3" />
                      <h1 className="text-xl font-bold text-white">Trading Bot</h1>
                  </div>
                  <div className="mt-5 h-0 flex-1 overflow-y-auto">
                    <nav className="space-y-1 px-2">
                      {navigation.map((item) => (
                        <Link
                          key={item.name}
                          href={item.href}
                          className={classNames(
                            pathname === item.href
                              ? 'bg-gray-800 text-white'
                              : 'text-gray-400 hover:bg-gray-800 hover:text-white',
                            'group flex items-center px-2 py-2 text-base font-medium rounded-md'
                          )}
                        >
                          <item.icon
                            className="mr-4 h-6 w-6 flex-shrink-0 text-gray-500"
                            aria-hidden="true"
                          />
                          {item.name}
                        </Link>
                      ))}
                      {isAdmin && (
                        <>
                          <Link
                            href="/dashboard/admin"
                            className={classNames(
                              pathname === '/dashboard/admin'
                                ? 'bg-gray-800 text-white'
                                : 'text-gray-400 hover:bg-gray-800 hover:text-white',
                              'group flex items-center px-2 py-2 text-base font-medium rounded-md'
                            )}
                          >
                            <ShieldCheckIcon
                              className="mr-4 h-6 w-6 flex-shrink-0 text-gray-500"
                              aria-hidden="true"
                            />
                            Admin
                          </Link>
                          <Link
                            href="/dashboard/admin/cassava-data"
                            className={classNames(
                              pathname === '/dashboard/admin/cassava-data'
                                ? 'bg-gray-800 text-white'
                                : 'text-gray-400 hover:bg-gray-800 hover:text-white',
                              'group flex items-center pl-12 py-2 text-base font-medium rounded-md'
                            )}
                          >
                            <TableCellsIcon className="mr-4 h-5 w-5 flex-shrink-0 text-indigo-400" aria-hidden="true" />
                            Cassava BOT Data
                          </Link>
                        </>
                      )}
                    </nav>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
              <div className="w-14 flex-shrink-0" aria-hidden="true">
                {/* Dummy element to force sidebar to shrink to fit close icon */}
              </div>
            </div>
          </Dialog>
        </Transition.Root>

        {/* Static sidebar for desktop */}
        <div className="hidden md:fixed md:inset-y-0 md:flex md:w-64 md:flex-col">
            <div className="flex flex-grow flex-col overflow-y-auto bg-gray-900 pt-5">
                <div className="flex flex-shrink-0 items-center px-4">
                    <ChartBarIcon className="h-8 w-8 text-blue-500 mr-3" />
                    <h1 className="text-xl font-bold text-white">Trading Bot</h1>
                </div>
                <div className="mt-5 flex flex-1 flex-col">
                    <nav className="flex-1 space-y-1 px-2 pb-4">
                        {navigation.map((item) => (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={classNames(
                                    pathname === item.href ? 'bg-gray-800 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-white',
                                    'group flex items-center px-2 py-2 text-sm font-medium rounded-md'
                                )}
                            >
                                <item.icon className="mr-3 h-6 w-6 flex-shrink-0 text-gray-500" />
                                {item.name}
                            </Link>
                        ))}
                        {isAdmin && (
                          <>
                            <Link
                              href="/dashboard/admin"
                              className={classNames(
                                pathname === '/dashboard/admin'
                                  ? 'bg-gray-800 text-white'
                                  : 'text-gray-400 hover:bg-gray-800 hover:text-white',
                                'group flex items-center px-2 py-2 text-sm font-medium rounded-md'
                              )}
                            >
                              <ShieldCheckIcon className="mr-3 h-6 w-6 flex-shrink-0 text-gray-500" />
                              Admin
                            </Link>
                            <Link
                              href="/dashboard/admin/cassava-data"
                              className={classNames(
                                pathname === '/dashboard/admin/cassava-data'
                                  ? 'bg-gray-800 text-white'
                                  : 'text-gray-400 hover:bg-gray-800 hover:text-white',
                                'group flex items-center pl-10 py-2 text-sm font-medium rounded-md'
                              )}
                            >
                              <TableCellsIcon className="mr-3 h-5 w-5 flex-shrink-0 text-indigo-400" />
                              Cassava BOT Data
                            </Link>
                          </>
                        )}
                    </nav>
                </div>
            </div>
        </div>

        <div className="md:pl-64">
            <div className="sticky top-0 z-10 flex h-16 flex-shrink-0 bg-gray-900 shadow">
                <button
                    type="button"
                    className="border-r border-gray-700 px-4 text-gray-400 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 md:hidden"
                    onClick={() => setSidebarOpen(true)}
                >
                    <span className="sr-only">Open sidebar</span>
                    <Bars3Icon className="h-6 w-6" />
                </button>
                 <div className="flex flex-1 items-center justify-end px-4">
                    <Menu as="div" className="relative ml-3">
                        <div>
                            <Menu.Button className="flex max-w-xs items-center rounded-full bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800">
                                <span className="sr-only">Open user menu</span>
                                <img
                                    className="h-8 w-8 rounded-full"
                                    src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
                                    alt=""
                                />
                            </Menu.Button>
                        </div>
                        <Transition
                            as={Fragment}
                            enter="transition ease-out duration-100"
                            enterFrom="transform opacity-0 scale-95"
                            enterTo="transform opacity-100 scale-100"
                            leave="transition ease-in duration-75"
                            leaveFrom="transform opacity-100 scale-100"
                            leaveTo="transform opacity-0 scale-95"
                        >
                            <Menu.Items className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                                <Menu.Item>
                                    {({ active }) => (
                                        <a href="#" className={classNames(active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700')}>
                                            Your Profile
                                        </a>
                                    )}
                                </Menu.Item>
                                <Menu.Item>
                                    {({ active }) => (
                                        <a href="#" className={classNames(active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700')}>
                                            Settings
                                        </a>
                                    )}
                                </Menu.Item>
                                <Menu.Item>
                                    {({ active }) => (
                                        <button
                                            onClick={() => setShowPasswordModal(true)}
                                            className={classNames(active ? 'bg-gray-100' : '', 'block w-full text-left px-4 py-2 text-sm text-gray-700')}
                                        >
                                            Change Password
                                        </button>
                                    )}
                                </Menu.Item>
                                <Menu.Item>
                                    {({ active }) => (
                                        <button
                                            onClick={handleLogout}
                                            className={classNames(active ? 'bg-gray-100' : '', 'block w-full text-left px-4 py-2 text-sm text-gray-700')}
                                        >
                                            Sign out
                                        </button>
                                    )}
                                </Menu.Item>
                            </Menu.Items>
                        </Transition>
                    </Menu>
                 </div>
            </div>

            <main className="flex-1">
                <div className="py-6">
                    <div className="mx-auto max-w-7xl px-4 sm:px-6 md:px-8">
                        {children}
                    </div>
                </div>
            </main>
        </div>

        {/* User Password Change Modal */}
        <PasswordChangeModal
          isOpen={showPasswordModal}
          onClose={() => setShowPasswordModal(false)}
          onSuccess={() => {
            // Could add additional success handling here if needed
          }}
        />
    </div>
  );
} 
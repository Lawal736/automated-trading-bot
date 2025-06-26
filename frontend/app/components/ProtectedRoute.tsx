'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export default function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { user, loading, isAuthenticated, isAdmin } = useAuth();
  const router = useRouter();
  const [hasCheckedAuth, setHasCheckedAuth] = useState(false);

  useEffect(() => {
    console.log('ProtectedRoute: loading=', loading, 'isAuthenticated=', isAuthenticated, 'user=', user);
    
    if (!loading) {
      // Add a small delay to ensure auth state is properly set
      const timer = setTimeout(() => {
        if (!isAuthenticated) {
          console.log('ProtectedRoute: User not authenticated, redirecting to login');
          router.push('/login');
        } else if (requireAdmin && !isAdmin) {
          console.log('ProtectedRoute: User not admin, redirecting to dashboard');
          router.push('/dashboard');
        } else {
          console.log('ProtectedRoute: User authenticated and authorized');
        }
        setHasCheckedAuth(true);
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [loading, isAuthenticated, isAdmin, requireAdmin, router, user]);

  if (loading || !hasCheckedAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (requireAdmin && !isAdmin) {
    return null;
  }

  return <>{children}</>;
} 
import Link from 'next/link';

export default function HomePage() {
  return (
    // Force rebuild
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white">
      <div className="text-center">
        <h1 className="text-5xl font-extrabold mb-4">
          Welcome to the Automated Trading Bot
        </h1>
        <p className="text-lg text-gray-400 mb-8">
          Your personal platform for building and deploying trading strategies.
        </p>
        <div className="space-x-4">
          <Link href="/login" className="px-6 py-3 font-semibold text-white bg-blue-600 rounded-md hover:bg-blue-700">
            Login
          </Link>
          <Link href="/register" className="px-6 py-3 font-semibold text-white bg-gray-700 rounded-md hover:bg-gray-600">
            Register
          </Link>
        </div>
      </div>
    </div>
  );
} 
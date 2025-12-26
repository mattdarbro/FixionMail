/**
 * Login Page
 *
 * Magic link authentication with email.
 */

import { useState, FormEvent } from 'react';
import { useAuth } from '../contexts/AuthContext';

export function LoginPage() {
  const { signInWithMagicLink } = useAuth();
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const { error } = await signInWithMagicLink(email);

    setIsLoading(false);

    if (error) {
      setError(error.message);
    } else {
      setSuccess(true);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="text-5xl mb-4">📬</div>
          <h1 className="text-2xl font-bold text-stone-800 mb-2">
            Check Your Email!
          </h1>
          <p className="text-stone-600 mb-6">
            We've sent a magic link to <strong>{email}</strong>. Click the link
            to sign in to FixionMail.
          </p>
          <p className="text-sm text-stone-500">
            Didn't receive it? Check your spam folder or{' '}
            <button
              onClick={() => setSuccess(false)}
              className="text-amber-600 hover:text-amber-700 font-medium"
            >
              try again
            </button>
            .
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo */}
        <div className="text-center mb-8">
          <span className="text-6xl block mb-4">🎭</span>
          <h1 className="text-3xl font-bold text-amber-800">FixionMail</h1>
          <p className="text-stone-600 mt-2">Your Personal Story Studio</p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-xl font-semibold text-stone-800 mb-2">
            Welcome Back
          </h2>
          <p className="text-stone-600 mb-6">
            Enter your email to receive a magic link.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-stone-700 mb-1"
              >
                Email Address
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full px-4 py-3 border border-stone-300 rounded-lg
                           focus:ring-2 focus:ring-amber-500 focus:border-transparent
                           placeholder:text-stone-400"
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || !email}
              className="w-full px-4 py-3 bg-amber-600 text-white rounded-lg font-semibold
                         hover:bg-amber-700 transition-colors
                         disabled:bg-stone-300 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Sending...
                </span>
              ) : (
                'Send Magic Link'
              )}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-stone-500">
            New to FixionMail?{' '}
            <a href="/signup" className="text-amber-600 hover:text-amber-700 font-medium">
              Start your free trial
            </a>
          </div>
        </div>

        {/* Features hint */}
        <div className="mt-8 text-center text-sm text-stone-500">
          <p>✨ Daily personalized stories delivered to your inbox</p>
        </div>
      </div>
    </div>
  );
}

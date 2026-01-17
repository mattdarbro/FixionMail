/**
 * Signup Page
 *
 * Email/password registration for new users.
 */

import { useState, FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function SignupPage() {
  const { signUp } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate passwords match
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // Validate password length
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setIsLoading(true);

    const { error } = await signUp(email, password);

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
          <div className="text-5xl mb-4">🎉</div>
          <h1 className="text-2xl font-bold text-stone-800 mb-2">
            Account Created!
          </h1>
          <p className="text-stone-600 mb-6">
            Check your email at <strong>{email}</strong> to confirm your account,
            then you can sign in.
          </p>
          <Link
            to="/login"
            className="inline-block px-6 py-3 bg-amber-600 text-white rounded-lg font-semibold
                       hover:bg-amber-700 transition-colors"
          >
            Go to Sign In
          </Link>
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

        {/* Signup Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-xl font-semibold text-stone-800 mb-2">
            Start Your Free Trial
          </h2>
          <p className="text-stone-600 mb-6">
            Create an account to receive personalized stories.
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
                           bg-white text-stone-800
                           focus:ring-2 focus:ring-amber-500 focus:border-transparent
                           placeholder:text-stone-400"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-stone-700 mb-1"
              >
                Password
              </label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 6 characters"
                required
                minLength={6}
                className="w-full px-4 py-3 border border-stone-300 rounded-lg
                           bg-white text-stone-800
                           focus:ring-2 focus:ring-amber-500 focus:border-transparent
                           placeholder:text-stone-400"
              />
            </div>

            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-stone-700 mb-1"
              >
                Confirm Password
              </label>
              <input
                type="password"
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                required
                minLength={6}
                className="w-full px-4 py-3 border border-stone-300 rounded-lg
                           bg-white text-stone-800
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
              disabled={isLoading || !email || !password || !confirmPassword}
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
                  Creating account...
                </span>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-stone-500">
            Already have an account?{' '}
            <Link to="/login" className="text-amber-600 hover:text-amber-700 font-medium">
              Sign in
            </Link>
          </div>
        </div>

        {/* What you get */}
        <div className="mt-8 bg-white/50 rounded-xl p-6">
          <h3 className="font-semibold text-stone-700 mb-3">What you'll get:</h3>
          <ul className="space-y-2 text-sm text-stone-600">
            <li className="flex items-center gap-2">
              <span className="text-amber-500">✓</span>
              Daily personalized stories in your inbox
            </li>
            <li className="flex items-center gap-2">
              <span className="text-amber-500">✓</span>
              Choose your genre and protagonist
            </li>
            <li className="flex items-center gap-2">
              <span className="text-amber-500">✓</span>
              Interactive choices that shape your story
            </li>
            <li className="flex items-center gap-2">
              <span className="text-amber-500">✓</span>
              Chat with Fixion about your stories
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

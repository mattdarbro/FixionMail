/**
 * Auth Callback Page
 *
 * Handles the magic link callback from Supabase auth.
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { supabase } from '../utils/supabase';
import { useAuth } from '../contexts/AuthContext';

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, isLoading: authLoading } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get the hash fragment for the token
        const hashParams = new URLSearchParams(window.location.hash.slice(1));
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');

        if (accessToken && refreshToken) {
          // Set the session using the tokens from the URL
          const { error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });

          if (error) {
            throw error;
          }
        } else {
          // Handle code exchange flow (PKCE)
          const code = searchParams.get('code');
          if (code) {
            const { error } = await supabase.auth.exchangeCodeForSession(code);
            if (error) {
              throw error;
            }
          }
        }
      } catch (err) {
        console.error('Auth callback error:', err);
        setError(err instanceof Error ? err.message : 'Authentication failed');
      }
    };

    handleCallback();
  }, [searchParams]);

  // Redirect once authenticated
  useEffect(() => {
    if (!authLoading && user) {
      // Check if onboarding is complete
      if (user.onboarding_completed) {
        navigate('/dashboard');
      } else {
        navigate('/onboarding');
      }
    }
  }, [user, authLoading, navigate]);

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="text-5xl mb-4">😕</div>
          <h1 className="text-2xl font-bold text-stone-800 mb-2">
            Authentication Failed
          </h1>
          <p className="text-stone-600 mb-6">{error}</p>
          <a
            href="/login"
            className="inline-block px-6 py-3 bg-amber-600 text-white rounded-lg font-semibold
                       hover:bg-amber-700 transition-colors"
          >
            Try Again
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex items-center justify-center p-4">
      <div className="text-center">
        <div className="text-5xl mb-4 animate-bounce">🎭</div>
        <h1 className="text-xl font-semibold text-stone-800 mb-2">
          Signing you in...
        </h1>
        <p className="text-stone-600">Just a moment while we prepare your experience.</p>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { Bot, LoaderCircle, LogIn } from 'lucide-react';
import { requireSupabase, supabaseConfigured } from '../services/supabase';

export const AuthGate: React.FC = () => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setIsSubmitting(true);

    try {
      const client = requireSupabase();
      if (isSignUp) {
        const { data, error: signUpError } = await client.auth.signUp({ email, password });
        if (signUpError) throw signUpError;
        if (!data.session) {
          setNotice('Check your email to confirm your account, then sign in.');
        }
      } else {
        const { error: signInError } = await client.auth.signInWithPassword({ email, password });
        if (signInError) throw signInError;
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Authentication failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <section className="glass-panel w-full max-w-md p-7 sm:p-9">
        <div className="mb-7 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-300">
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">CogniOps</h1>
            <p className="text-xs text-slate-400">Private operations workspace</p>
          </div>
        </div>

        {!supabaseConfigured ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
            Set <code>VITE_SUPABASE_URL</code> and <code>VITE_SUPABASE_ANON_KEY</code> in the
            frontend environment, then restart the app.
          </div>
        ) : (
          <>
            <h2 className="mb-1 text-lg font-semibold text-white">
              {isSignUp ? 'Create your account' : 'Welcome back'}
            </h2>
            <p className="mb-6 text-sm text-slate-400">
              Sign in to access your own transcripts and coordination runs.
            </p>

            {error && (
              <div role="alert" className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
                {error}
              </div>
            )}
            {notice && (
              <div role="status" className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
                {notice}
              </div>
            )}

            <form className="space-y-4" onSubmit={handleSubmit}>
              <label className="block text-sm font-medium text-slate-300">
                Email
                <input
                  className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </label>
              <label className="block text-sm font-medium text-slate-300">
                Password
                <input
                  className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white"
                  type="password"
                  autoComplete={isSignUp ? 'new-password' : 'current-password'}
                  minLength={8}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </label>
              <button className="btn btn-primary w-full" type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <LogIn className="h-4 w-4" />
                )}
                {isSubmitting ? 'Please wait…' : isSignUp ? 'Create account' : 'Sign in'}
              </button>
            </form>
            <button
              type="button"
              className="mt-5 w-full text-center text-sm text-indigo-300 hover:text-indigo-200"
              onClick={() => {
                setIsSignUp(!isSignUp);
                setError(null);
                setNotice(null);
              }}
            >
              {isSignUp ? 'Already have an account? Sign in' : 'New here? Create an account'}
            </button>
          </>
        )}
      </section>
    </main>
  );
};

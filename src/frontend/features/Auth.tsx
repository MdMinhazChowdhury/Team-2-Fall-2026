import { useEffect, useState, type FormEvent } from 'react';
import { request } from '../api/client';
import { Field } from '../components/Dialog';

type Mode =
  'login' | 'register' | 'forgot' | 'verify' | 'reset' | 'verification';
export function Auth({ done }: { done: () => void }) {
  const [link] = useState(() => {
    const values = new URLSearchParams(location.hash.slice(1));
    const result = { verify: values.get('verify'), reset: values.get('reset') };
    return result;
  });
  useEffect(() => {
    if (link.verify || link.reset)
      history.replaceState(null, '', location.pathname);
  }, [link]);
  const [mode, setMode] = useState<Mode>(
    link.verify ? 'verify' : link.reset ? 'reset' : 'login',
  );
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  const labels: Record<Mode, string> = {
    login: 'Log in',
    register: 'Create account',
    forgot: 'Reset password',
    verify: 'Verify email',
    reset: 'Set new password',
    verification: 'Resend verification',
  };
  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setMessage('');
    try {
      const data =
        mode === 'verify'
          ? { token: link.verify }
          : mode === 'reset'
            ? { token: link.reset, password }
            : mode === 'forgot' || mode === 'verification'
              ? { email }
              : { email, password };
      const result = await request<{ message?: string }>(
        `/auth/${mode}`,
        'POST',
        data,
      );
      setPassword('');
      if (mode === 'login') done();
      else {
        setMessage(result.message || 'Done');
        if (mode === 'verify' || mode === 'reset') setMode('login');
      }
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setPending(false);
    }
  }
  return (
    <main className="auth-layout">
      <section className="auth-story">
        <p className="eyebrow">YOUR WORK, IN FOCUS</p>
        <h1>
          A little structure.
          <br />A clearer day.
        </h1>
        <p>
          Bring your assignments, everyday tasks, and next big ideas together.
        </p>
        <div className="sample-card">
          <span className="checkmark">✓</span>
          <div>
            <strong>Make room for what matters</strong>
            <p>One task at a time.</p>
          </div>
        </div>
        <p className="small">
          Private lists. Clear priorities. Steady progress.
        </p>
      </section>
      <section className="auth-card">
        <p className="eyebrow">WELCOME TO TASKTRACK</p>
        <h2>{labels[mode]}</h2>
        <p className="muted">Your plans have a place here.</p>
        <form onSubmit={submit}>
          <fieldset disabled={pending}>
            {mode !== 'verify' && mode !== 'reset' && (
              <Field label="Email">
                <input
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  maxLength={254}
                />
              </Field>
            )}
            {['login', 'register', 'reset'].includes(mode) && (
              <Field label={mode === 'reset' ? 'New password' : 'Password'}>
                <input
                  type="password"
                  autoComplete={
                    mode === 'login' ? 'current-password' : 'new-password'
                  }
                  minLength={mode === 'login' ? 1 : 12}
                  maxLength={128}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </Field>
            )}
            {['register', 'reset'].includes(mode) && (
              <p className="small">
                Use 12–128 characters. Spaces are preserved.
              </p>
            )}
            <button className="primary wide" type="submit">
              {pending ? 'Working…' : labels[mode]}
            </button>
          </fieldset>
        </form>
        {message && (
          <p role="status" className="notice">
            {message}
          </p>
        )}
        <nav aria-label="Account options" className="auth-links">
          {(['login', 'register', 'forgot', 'verification'] as Mode[])
            .filter((value) => value !== mode)
            .map((value) => (
              <button
                disabled={pending}
                key={value}
                onClick={() => {
                  setMode(value);
                  setMessage('');
                }}
              >
                {labels[value]}
              </button>
            ))}
        </nav>
      </section>
    </main>
  );
}

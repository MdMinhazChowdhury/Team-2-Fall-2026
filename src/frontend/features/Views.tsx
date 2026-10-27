import { useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { request, type Account, type Task, type TaskPage } from '../api/client';
import { Field } from '../components/Dialog';
import { todayInZone } from '../utilities/dates';

export function CalendarView({ open }: { open: (task: Task) => void }) {
  const [anchor, setAnchor] = useState(new Date());
  const [mode, setMode] = useState('month');
  const first = new Date(
    anchor.getFullYear(),
    anchor.getMonth(),
    mode === 'month' ? 1 : anchor.getDate() - anchor.getDay(),
  );
  const end =
    mode === 'month'
      ? new Date(first.getFullYear(), first.getMonth() + 1, 0)
      : new Date(first.getFullYear(), first.getMonth(), first.getDate() + 6);
  const iso = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  const tasks = useQuery({
    queryKey: ['calendar', iso(first), iso(end)],
    queryFn: async () => {
      const items: Task[] = [];
      let page = 1;
      while (true) {
        const result = await request<TaskPage>(
          `/tasks?due_from=${iso(first)}&due_through=${iso(end)}&page_size=100&page=${page++}`,
        );
        items.push(...result.items);
        if (items.length >= result.total) return items;
      }
    },
  });
  const days: Date[] = [];
  for (
    let date = new Date(first);
    date <= end;
    date = new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1)
  )
    days.push(date);
  const navigate = (delta: number) =>
    setAnchor(
      mode === 'month'
        ? new Date(anchor.getFullYear(), anchor.getMonth() + delta, 1)
        : new Date(
            anchor.getFullYear(),
            anchor.getMonth(),
            anchor.getDate() + delta * 7,
          ),
    );
  return (
    <section>
      <div className="section-title">
        <h2>Calendar</h2>
        <div className="actions">
          <button onClick={() => navigate(-1)} aria-label="Previous period">
            ←
          </button>
          <strong>
            {anchor.toLocaleDateString(undefined, {
              month: 'long',
              year: 'numeric',
            })}
          </strong>
          <button onClick={() => navigate(1)} aria-label="Next period">
            →
          </button>
          <select
            aria-label="Calendar view"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="month">Month</option>
            <option value="week">Week</option>
          </select>
        </div>
      </div>
      {tasks.error && <p role="alert">{tasks.error.message}</p>}
      {tasks.isPending && <p role="status">Loading calendar…</p>}
      <div className="calendar">
        {days.map((day) => (
          <section key={iso(day)} className="calendar-day">
            <h3>
              {day.toLocaleDateString(undefined, {
                weekday: 'short',
                day: 'numeric',
              })}
            </h3>
            {tasks.data
              ?.filter((task) => task.due_date === iso(day))
              .map((task) => (
                <button
                  className="calendar-task"
                  key={task.id}
                  onClick={() => open(task)}
                >
                  {task.title}
                </button>
              ))}
          </section>
        ))}
      </div>
    </section>
  );
}

export function Reports({ timezone }: { timezone: string }) {
  const today = todayInZone(timezone);
  const [start, setStart] = useState(today.slice(0, 8) + '01');
  const [end, setEnd] = useState(today);
  const report = useQuery({
    queryKey: ['reports', start, end],
    queryFn: () =>
      request<{
        completions: Record<string, number>;
        status: Record<string, number>;
      }>(`/reports?start=${start}&end=${end}`),
    enabled: Boolean(start && end),
  });
  return (
    <section className="panel">
      <h2>Productivity report</h2>
      <p className="muted">
        Completion events by day in your account timezone. Earlier completions
        remain in this history when a task is reopened or deleted.
      </p>
      <div className="form-grid">
        <Field label="From">
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            required
          />
        </Field>
        <Field label="Through">
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            required
          />
        </Field>
      </div>
      {report.error && <p role="alert">{report.error.message}</p>}
      {report.data && (
        <>
          <p className="report-total">
            {Object.values(report.data.completions).reduce((a, b) => a + b, 0)}{' '}
            <span>tasks completed</span>
          </p>
          <div className="report-list">
            {Object.entries(report.data.completions).map(([date, count]) => (
              <div key={date}>
                <time>{date}</time>
                <meter
                  min={0}
                  max={Math.max(1, ...Object.values(report.data.completions))}
                  value={count}
                  aria-label={`${date}: ${count} completed tasks`}
                />
                <strong>{count}</strong>
              </div>
            ))}
          </div>
          <p>
            {Object.entries(report.data.status)
              .map(([name, value]) => `${name.replaceAll('_', ' ')}: ${value}`)
              .join(' · ')}
          </p>
        </>
      )}
    </section>
  );
}

export function Notifications({ open }: { open: (task: Task) => void }) {
  const notifications = useQuery({
    queryKey: ['notifications'],
    queryFn: () =>
      request<
        {
          id: string;
          task_id: string;
          title: string;
          read_at: string | null;
          created_at: string;
        }[]
      >('/notifications'),
    refetchInterval: 30000,
  });
  const [error, setError] = useState('');
  async function act(id: string, taskId: string) {
    try {
      await request(`/notifications/${id}/read`, 'POST');
      await notifications.refetch();
      open(await request<Task>(`/tasks/${taskId}`));
    } catch (error) {
      setError((error as Error).message);
    }
  }
  return (
    <section className="panel">
      <h2>Notifications</h2>
      {(error || notifications.error) && (
        <p role="alert">{error || notifications.error?.message}</p>
      )}
      {notifications.data?.length === 0 && <p>You’re all caught up.</p>}
      {notifications.data?.map((item) => (
        <article className="notification" key={item.id}>
          <button onClick={() => act(item.id, item.task_id)}>
            {item.title}
          </button>
          <span>
            {item.read_at ? 'Read' : 'Unread'} ·{' '}
            {new Date(item.created_at).toLocaleString()}
          </span>
        </article>
      ))}
    </section>
  );
}

export function AdminAccounts({
  confirm,
}: {
  confirm: (message: string, action: () => Promise<void>) => void;
}) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'USER' | 'ADMIN'>('USER');
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  const accounts = useQuery({
    queryKey: ['admin-accounts'],
    queryFn: () => request<Account[]>('/admin/accounts'),
  });

  async function create(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setMessage('');
    try {
      await request('/admin/accounts', 'POST', { email, password, role });
      setEmail('');
      setPassword('');
      setRole('USER');
      setMessage('Account created.');
      await accounts.refetch();
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setPending(false);
    }
  }

  async function setActive(account: Account, active: boolean) {
    setPending(true);
    setMessage('');
    try {
      await request('/admin/accounts/' + account.id + '/status', 'PATCH', {
        active,
      });
      setMessage(active ? 'Account enabled.' : 'Account disabled.');
      await accounts.refetch();
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setPending(false);
    }
  }

  async function remove(account: Account) {
    setPending(true);
    setMessage('');
    try {
      await request('/admin/accounts/' + account.id, 'DELETE', {
        confirmed: true,
      });
      setMessage('Account deleted.');
      await accounts.refetch();
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="settings-grid">
      <div className="panel">
        <h2>Create account</h2>
        <p>Create a verified user or administrator account.</p>
        <form onSubmit={create}>
          <fieldset disabled={pending}>
            <Field label="Email">
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </Field>
            <Field label="Temporary password">
              <input
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={12}
                maxLength={128}
                required
              />
            </Field>
            <Field label="Role">
              <select
                value={role}
                onChange={(event) =>
                  setRole(event.target.value as 'USER' | 'ADMIN')
                }
              >
                <option value="USER">User</option>
                <option value="ADMIN">Administrator</option>
              </select>
            </Field>
            <button className="primary">Create account</button>
          </fieldset>
        </form>
      </div>
      <div className="panel">
        <h2>Accounts</h2>
        {accounts.isPending && <p>Loading accounts…</p>}
        {accounts.error && <p role="alert">{accounts.error.message}</p>}
        {accounts.data?.map((account) => (
          <div className="session-row" key={account.id}>
            <p>
              {account.email}
              <br />
              <small>
                {account.role === 'ADMIN' ? 'Administrator' : 'User'} ·{' '}
                {account.active ? 'Active' : 'Disabled'}
              </small>
            </p>
            <div>
              <button
                disabled={pending}
                onClick={() => setActive(account, !account.active)}
              >
                {account.active ? 'Disable' : 'Enable'}
              </button>{' '}
              <button
                className="danger"
                disabled={pending}
                onClick={() =>
                  confirm('Permanently delete ' + account.email + '?', () =>
                    remove(account),
                  )
                }
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
    </section>
  );
}

export function Settings({
  account,
  changed,
  signedOut,
  confirm,
}: {
  account: Account;
  changed: () => void;
  signedOut: () => void;
  confirm: (message: string, action: () => Promise<void>) => void;
}) {
  const [zone, setZone] = useState(account.timezone);
  const [email, setEmail] = useState(account.email_reminders);
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [deletion, setDeletion] = useState('');
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  const sessions = useQuery({
    queryKey: ['sessions'],
    queryFn: () =>
      request<
        {
          id: string;
          current: boolean;
          user_agent: string;
          created_at: string;
        }[]
      >('/me/sessions'),
  });
  async function act(path: string, method: string, data?: unknown) {
    setPending(true);
    setMessage('');
    try {
      const result = await request<{ message?: string }>(path, method, data);
      setMessage(result.message || 'Settings saved');
      setCurrent('');
      setPassword('');
      changed();
      await sessions.refetch();
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="settings-grid">
      <div className="panel">
        <h2>Preferences</h2>
        <p>{account.email}</p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            act('/me', 'PATCH', { timezone: zone, email_reminders: email });
          }}
        >
          <fieldset disabled={pending}>
            <Field label="Timezone (IANA name)">
              <input
                value={zone}
                onChange={(e) => setZone(e.target.value)}
                required
                list="timezones"
              />
              <datalist id="timezones">
                {[
                  'UTC',
                  'America/New_York',
                  'America/Chicago',
                  'America/Los_Angeles',
                  'Europe/London',
                  'Asia/Tokyo',
                ].map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </datalist>
            </Field>
            <label>
              <input
                type="checkbox"
                checked={email}
                onChange={(e) => setEmail(e.target.checked)}
              />{' '}
              Allow email reminders
            </label>
            <button className="primary">Save preferences</button>
          </fieldset>
        </form>
      </div>
      <div className="panel">
        <h2>Change password</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            act('/me/password', 'POST', {
              current_password: current,
              new_password: password,
            });
          }}
        >
          <fieldset disabled={pending}>
            <Field label="Current password">
              <input
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                required
                maxLength={128}
              />
            </Field>
            <Field label="New password">
              <input
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={12}
                maxLength={128}
              />
            </Field>
            <button>Change password and revoke other sessions</button>
          </fieldset>
        </form>
      </div>
      <div className="panel">
        <h2>Active sessions</h2>
        <button
          disabled={pending}
          onClick={() =>
            confirm('Revoke every session, including this one?', async () => {
              await request('/me/sessions', 'DELETE');
              signedOut();
            })
          }
        >
          Revoke all sessions
        </button>
        {sessions.error && <p role="alert">{sessions.error.message}</p>}
        {sessions.data?.map((session) => (
          <div className="session-row" key={session.id}>
            <p>
              {session.current ? 'This session' : 'Other session'}
              <br />
              <small>{session.user_agent || 'Unknown browser'}</small>
            </p>
            <button
              disabled={pending}
              onClick={() =>
                confirm('Revoke this session?', async () => {
                  await request(`/me/sessions/${session.id}`, 'DELETE');
                  if (session.current) signedOut();
                  else {
                    changed();
                    await sessions.refetch();
                  }
                })
              }
            >
              Revoke
            </button>
          </div>
        ))}
      </div>
      <div className="panel danger-zone">
        <h2>Delete account</h2>
        <p>
          This permanently removes your account, lists, tasks, and private
          records.
        </p>
        <Field label="Confirm current password">
          <input
            type="password"
            autoComplete="current-password"
            value={deletion}
            onChange={(e) => setDeletion(e.target.value)}
            maxLength={128}
          />
        </Field>
        <button
          className="danger"
          disabled={!deletion || pending}
          onClick={() =>
            confirm(
              'Permanently delete your account and all its data? This cannot be undone.',
              async () => {
                await request('/me', 'DELETE', {
                  current_password: deletion,
                  confirmed: true,
                });
                signedOut();
              },
            )
          }
        >
          Delete my account
        </button>
      </div>
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
    </section>
  );
}

export function Portability({ changed }: { changed: () => void }) {
  const [preview, setPreview] = useState<{
    id: string;
    lists: number;
    tasks: number;
    tags: number;
    message: string;
  } | null>(null);
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  async function upload(file: File | undefined) {
    setPreview(null);
    setMessage('');
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setMessage('File must be at most 2 MiB');
      return;
    }
    setPending(true);
    try {
      const payload = JSON.parse(await file.text());
      setPreview(await request('/import/preview', 'POST', payload));
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setPending(false);
    }
  }
  async function download() {
    setPending(true);
    setMessage('');
    try {
      const job = await request<{ id: string }>('/exports', 'POST');
      setMessage('Preparing your export in the background…');
      let ready = false;
      for (let attempt = 0; attempt < 90; attempt++) {
        const status = await request<{ status: string }>(`/exports/${job.id}`);
        if (status.status === 'ready') {
          ready = true;
          break;
        }
        if (status.status === 'failed')
          throw new Error('Export exceeded the supported limits.');
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
      }
      if (!ready)
        throw new Error(
          'Export is still waiting for the worker. Check that the worker and scheduler are running, then retry.',
        );
      const payload = await request(`/exports/${job.id}/download`);
      setMessage('Export ready.');
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(payload, null, 2)], {
          type: 'application/json',
        }),
      );
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'tasktrack-export.json';
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="panel">
      <h2>Your data, with you</h2>
      <p>
        Export active lists, tasks, checklists, and tags in TaskTrack format v1.
        Schedules, reminders, activity history, and Trash are excluded.
      </p>
      <button disabled={pending} onClick={download}>
        Download export
      </button>
      <h3>Import from a TaskTrack export</h3>
      <p>
        Maximum 2 MiB, 100 lists, 500 tags and 5,000 tasks. Preview before
        applying. New lists/tasks are added; existing data is retained.
      </p>
      <Field label="Choose JSON export">
        <input
          type="file"
          accept=".json,application/json"
          disabled={pending}
          onChange={(e) => upload(e.target.files?.[0])}
        />
      </Field>
      {preview && (
        <div className="notice">
          <p>
            {preview.lists} lists · {preview.tasks} tasks · {preview.tags} tags
          </p>
          <p>{preview.message}</p>
          <button
            disabled={pending}
            className="primary"
            onClick={async () => {
              setPending(true);
              try {
                const result = await request<{ message: string }>(
                  `/import/${preview.id}/apply`,
                  'POST',
                );
                setMessage(result.message);
                setPreview(null);
                changed();
              } catch (error) {
                setMessage((error as Error).message);
              } finally {
                setPending(false);
              }
            }}
          >
            Confirm import
          </button>
          <button disabled={pending} onClick={() => setPreview(null)}>
            Cancel
          </button>
        </div>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}

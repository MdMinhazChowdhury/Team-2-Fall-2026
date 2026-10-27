import { useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CheckCheck,
  CalendarDays,
  ChartNoAxesColumnIncreasing,
  ListTodo,
  Bell,
  Settings2,
  Users,
  ArrowDownToLine,
  Trash2,
  Plus,
  LogOut,
  Pencil,
} from 'lucide-react';
import {
  request,
  taskInput,
  statusLabel,
  type Account,
  type Dashboard,
  type Task,
  type TaskList,
  type TaskPage,
  type Tag,
} from '../api/client';
import { TaskEditor } from '../features/TaskEditor';
import {
  AdminAccounts,
  CalendarView,
  Notifications,
  Portability,
  Reports,
  Settings,
} from '../features/Views';
import { Dialog, Field } from '../components/Dialog';

type View =
  | 'tasks'
  | 'calendar'
  | 'reports'
  | 'notifications'
  | 'settings'
  | 'admin'
  | 'data'
  | 'trash';
export function Workspace({
  account,
  signedOut,
}: {
  account: Account;
  signedOut: () => void;
}) {
  const cache = useQueryClient();
  const [view, setView] = useState<View>('tasks');
  const [filters, setFilters] = useState({
    q: '',
    list_id: '',
    status: '',
    priority: '',
    tag_id: '',
    due: '',
    sort: 'due_date',
  });
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Task[]>([]);
  const [editor, setEditor] = useState<{ task: Task | null } | null>(null);
  const [manage, setManage] = useState<{
    kind: 'list' | 'tag';
    id?: string;
    version?: number;
  } | null>(null);
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  const [confirmation, setConfirmation] = useState<{
    message: string;
    action: () => Promise<void>;
  } | null>(null);
  const lists = useQuery({
    queryKey: ['lists'],
    queryFn: () => request<TaskList[]>('/lists'),
  });
  const tags = useQuery({
    queryKey: ['tags'],
    queryFn: () => request<Tag[]>('/tags'),
  });
  const dashboard = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => request<Dashboard>('/dashboard'),
  });
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value),
  );
  params.set('page', String(page));
  params.set('trashed', String(view === 'trash'));
  const tasks = useQuery({
    queryKey: ['tasks', filters, page, view],
    queryFn: () => request<TaskPage>(`/tasks?${params}`),
    enabled: view === 'tasks' || view === 'trash',
  });
  const changed = async () => {
    setSelected([]);
    await cache.invalidateQueries();
  };
  const confirm = (text: string, action: () => Promise<void>) =>
    setConfirmation({ message: text, action });
  async function mutate(path: string, method: string, data?: unknown) {
    setPending(true);
    setMessage('');
    try {
      await request(path, method, data);
      await changed();
      setMessage('Saved.');
      return true;
    } catch (error) {
      setMessage((error as Error).message);
      return false;
    } finally {
      setPending(false);
    }
  }
  function filter(value: Partial<typeof filters>) {
    setFilters((old) => ({ ...old, ...value }));
    setPage(1);
    setSelected([]);
  }
  function navigate(value: View) {
    setView(value);
    setPage(1);
    setSelected([]);
    setMessage('');
  }
  async function manageSubmit(event: FormEvent) {
    event.preventDefault();
    if (!manage) return;
    const path = manage.kind === 'list' ? '/lists' : '/tags';
    if (
      await mutate(
        path + (manage.id ? `/${manage.id}` : ''),
        manage.id ? 'PATCH' : 'POST',
        {
          name,
          ...(manage.kind === 'list' && manage.id
            ? { version: manage.version }
            : {}),
        },
      )
    )
      setManage(null);
  }
  const nav = [
    { value: 'tasks', label: 'My tasks', icon: ListTodo },
    { value: 'calendar', label: 'Calendar', icon: CalendarDays },
    { value: 'reports', label: 'Reports', icon: ChartNoAxesColumnIncreasing },
    { value: 'notifications', label: 'Notifications', icon: Bell },
    { value: 'trash', label: 'Trash', icon: Trash2 },
    { value: 'data', label: 'Import & export', icon: ArrowDownToLine },
    { value: 'settings', label: 'Settings', icon: Settings2 },
    ...(account.role === 'ADMIN'
      ? [{ value: 'admin' as const, label: 'Administration', icon: Users }]
      : []),
  ] as const;
  const activeError =
    lists.error ||
    tags.error ||
    dashboard.error ||
    (view === 'tasks' || view === 'trash' ? tasks.error : null);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <a href="#main" className="brand">
          <CheckCheck aria-hidden="true" />
          TaskTrack
          <span className="brand-dot" />
        </a>
        <p className="sidebar-caption">A LITTLE MORE ORGANIZED</p>
        <nav aria-label="Main navigation">
          {nav.map((item) => (
            <button
              key={item.value}
              className={view === item.value ? 'active' : ''}
              aria-current={view === item.value ? 'page' : undefined}
              onClick={() => navigate(item.value)}
            >
              <item.icon size={18} aria-hidden="true" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-section">
          <h2>Your lists</h2>
          <button
            aria-label="Create list"
            onClick={() => {
              setName('');
              setManage({ kind: 'list' });
            }}
          >
            <Plus size={16} />
          </button>
        </div>
        {lists.data?.map((list) => (
          <div className="sidebar-list" key={list.id}>
            <button
              onClick={() => {
                navigate('tasks');
                filter({ list_id: list.id });
              }}
            >
              <span className="list-dot" />
              {list.name}
            </button>
            <button
              aria-label={`Rename list ${list.name}`}
              onClick={() => {
                setName(list.name);
                setManage({ kind: 'list', id: list.id, version: list.version });
              }}
            >
              <Pencil size={13} />
            </button>
            <button
              aria-label={`Delete list ${list.name}`}
              onClick={() =>
                confirm(
                  `Delete “${list.name}”? Lists must be empty, including Trash.`,
                  async () => {
                    if (
                      await mutate(`/lists/${list.id}`, 'DELETE', {
                        confirmed: true,
                        version: list.version,
                      })
                    )
                      filter({ list_id: '' });
                  },
                )
              }
            >
              ×
            </button>
          </div>
        ))}
        <div className="sidebar-section">
          <h2>Tags</h2>
          <button
            aria-label="Create tag"
            onClick={() => {
              setName('');
              setManage({ kind: 'tag' });
            }}
          >
            <Plus size={16} />
          </button>
        </div>
        <div className="sidebar-tags">
          {tags.data?.map((tag) => (
            <div key={tag.id}>
              <button
                onClick={() => {
                  navigate('tasks');
                  filter({ tag_id: tag.id });
                }}
              >
                # {tag.name}
              </button>
              <button
                aria-label={`Rename tag ${tag.name}`}
                onClick={() => {
                  setName(tag.name);
                  setManage({ kind: 'tag', id: tag.id });
                }}
              >
                ✎
              </button>
              <button
                aria-label={`Delete tag ${tag.name}`}
                onClick={() =>
                  confirm(
                    `Delete tag “${tag.name}”? Tasks will be retained.`,
                    async () => {
                      if (await mutate(`/tags/${tag.id}`, 'DELETE'))
                        filter({ tag_id: '' });
                    },
                  )
                }
              >
                ×
              </button>
            </div>
          ))}
        </div>
        <div className="account-block">
          <span className="avatar">{account.email[0].toUpperCase()}</span>
          <span className="account-email">{account.email}</span>
          <button
            aria-label="Log out"
            disabled={pending}
            onClick={async () => {
              if (await mutate('/auth/logout', 'POST')) signedOut();
            }}
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <main id="main" className="workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">MAKE SPACE FOR PROGRESS</p>
            <h1>
              {view === 'tasks'
                ? 'Your day, a little clearer.'
                : nav.find((item) => item.value === view)?.label}
            </h1>
            <p className="muted">
              {view === 'tasks'
                ? 'Small steps add up. Let’s take the next one.'
                : 'Keep everything moving, at your pace.'}
            </p>
          </div>
          {view === 'tasks' && (
            <button
              className="primary"
              disabled={!lists.data?.length || pending}
              onClick={() => setEditor({ task: null })}
            >
              <Plus size={17} /> New task
            </button>
          )}
        </header>
        {message && (
          <div className="notice" role="status">
            {message}
            <button aria-label="Dismiss message" onClick={() => setMessage('')}>
              ×
            </button>
          </div>
        )}
        {activeError && (
          <div className="error" role="alert">
            {activeError.message}
            <button onClick={() => cache.invalidateQueries()}>Retry</button>
            <button onClick={signedOut}>Return to login</button>
          </div>
        )}
        {view === 'tasks' && (
          <section className="stats" aria-label="Task summary">
            {[
              {
                label: 'Due today',
                value: dashboard.data?.today,
                due: 'today',
              },
              {
                label: 'Coming up',
                value: dashboard.data?.upcoming,
                due: 'upcoming',
              },
              {
                label: 'Overdue',
                value: dashboard.data?.overdue,
                due: 'overdue',
              },
              {
                label: 'Completed',
                value: dashboard.data?.status.COMPLETED,
                due: '',
              },
            ].map((card, index) => (
              <button
                key={card.label}
                onClick={() =>
                  filter({
                    due: card.due,
                    status: index === 3 ? 'COMPLETED' : '',
                  })
                }
              >
                <span>{card.label}</span>
                <strong>{card.value ?? '—'}</strong>
                <small>
                  {index === 3
                    ? 'A moment for your progress'
                    : 'Keep your next step in sight'}
                </small>
              </button>
            ))}
          </section>
        )}
        {(view === 'tasks' || view === 'trash') && (
          <section className="task-section">
            <div className="section-title">
              <h2>
                {view === 'trash' ? 'Recently deleted' : 'Your tasks'}{' '}
                <span className="count">{tasks.data?.total ?? 0}</span>
              </h2>
              <button
                onClick={() => {
                  filter({
                    q: '',
                    list_id: '',
                    status: '',
                    priority: '',
                    tag_id: '',
                    due: '',
                    sort: 'due_date',
                  });
                }}
              >
                Reset filters
              </button>
            </div>
            {view === 'trash' && (
              <p className="muted">
                Restore tasks within 30 days. Permanent deletion cannot be
                undone.
              </p>
            )}
            <div className="filters">
              <Field label="Search titles">
                <input
                  type="search"
                  placeholder="Find a task…"
                  value={filters.q}
                  onChange={(e) => filter({ q: e.target.value })}
                />
              </Field>
              <Field label="Filter list">
                <select
                  value={filters.list_id}
                  onChange={(e) => filter({ list_id: e.target.value })}
                >
                  <option value="">All lists</option>
                  {lists.data?.map((list) => (
                    <option value={list.id} key={list.id}>
                      {list.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Filter status">
                <select
                  value={filters.status}
                  onChange={(e) => filter({ status: e.target.value })}
                >
                  <option value="">All statuses</option>
                  {Object.entries(statusLabel).map(([key, name]) => (
                    <option key={key} value={key}>
                      {name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Filter priority">
                <select
                  value={filters.priority}
                  onChange={(e) => filter({ priority: e.target.value })}
                >
                  <option value="">All priorities</option>
                  <option>LOW</option>
                  <option>MEDIUM</option>
                  <option>HIGH</option>
                </select>
              </Field>
              <Field label="Filter tag">
                <select
                  value={filters.tag_id}
                  onChange={(e) => filter({ tag_id: e.target.value })}
                >
                  <option value="">All tags</option>
                  {tags.data?.map((tag) => (
                    <option key={tag.id} value={tag.id}>
                      {tag.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Due category">
                <select
                  value={filters.due}
                  onChange={(e) => filter({ due: e.target.value })}
                >
                  <option value="">Any date</option>
                  <option value="today">Today</option>
                  <option value="upcoming">Upcoming</option>
                  <option value="overdue">Overdue</option>
                  <option value="undated">Undated</option>
                </select>
              </Field>
              <Field label="Sort by">
                <select
                  value={filters.sort}
                  onChange={(e) => filter({ sort: e.target.value })}
                >
                  <option value="due_date">Due date</option>
                  <option value="priority">Priority</option>
                  <option value="created_at">Newest first</option>
                </select>
              </Field>
            </div>
            {selected.length > 0 && (
              <div className="bulk-bar">
                <strong>{selected.length} selected</strong>
                <button
                  disabled={pending}
                  onClick={() =>
                    mutate('/bulk', 'POST', {
                      items: selected.map(({ id, version }) => ({
                        id,
                        version,
                      })),
                      action: 'complete',
                    })
                  }
                >
                  Complete selected
                </button>
                <select
                  disabled={pending}
                  aria-label="Move selected tasks"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value)
                      mutate('/bulk', 'POST', {
                        items: selected.map(({ id, version }) => ({
                          id,
                          version,
                        })),
                        action: 'move',
                        list_id: e.target.value,
                      });
                  }}
                >
                  <option value="">Move to…</option>
                  {lists.data?.map((list) => (
                    <option key={list.id} value={list.id}>
                      {list.name}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Reprioritize selected tasks"
                  disabled={pending}
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value)
                      mutate('/bulk', 'POST', {
                        items: selected.map(({ id, version }) => ({
                          id,
                          version,
                        })),
                        action: 'priority',
                        priority: e.target.value,
                      });
                  }}
                >
                  <option value="">Set priority…</option>
                  <option>LOW</option>
                  <option>MEDIUM</option>
                  <option>HIGH</option>
                </select>
                <button
                  disabled={pending}
                  onClick={() =>
                    confirm(
                      `Move ${selected.length} selected tasks to Trash?`,
                      async () => {
                        await mutate('/bulk', 'POST', {
                          items: selected.map(({ id, version }) => ({
                            id,
                            version,
                          })),
                          action: 'trash',
                          confirmed: true,
                        });
                      },
                    )
                  }
                >
                  Trash selected
                </button>
              </div>
            )}
            {tasks.isPending ? (
              <p role="status">Loading tasks…</p>
            ) : tasks.data?.items.length === 0 ? (
              <div className="empty">
                <ListTodo size={42} aria-hidden="true" />
                <h3>A little breathing room.</h3>
                <p>
                  {lists.data?.length
                    ? 'No tasks match these filters. Start fresh or adjust your view.'
                    : 'Create your first list to give your tasks a home.'}
                </p>
                {!lists.data?.length && (
                  <button
                    className="primary"
                    onClick={() => {
                      setName('');
                      setManage({ kind: 'list' });
                    }}
                  >
                    Create your first list
                  </button>
                )}
              </div>
            ) : (
              <div className="task-list">
                {tasks.data?.items.map((task) => (
                  <article className="task-row" key={task.id}>
                    {view !== 'trash' && (
                      <input
                        type="checkbox"
                        aria-label={`Select ${task.title}`}
                        checked={selected.some((item) => item.id === task.id)}
                        onChange={(e) =>
                          setSelected(
                            e.target.checked
                              ? [...selected, task]
                              : selected.filter((item) => item.id !== task.id),
                          )
                        }
                      />
                    )}
                    {view !== 'trash' && (
                      <button
                        className={`complete-button ${task.status === 'COMPLETED' ? 'done' : ''}`}
                        disabled={pending}
                        aria-label={`${task.status === 'COMPLETED' ? 'Reopen' : 'Complete'} ${task.title}`}
                        onClick={() =>
                          mutate(`/tasks/${task.id}`, 'PUT', {
                            ...taskInput(task),
                            version: task.version,
                            status:
                              task.status === 'COMPLETED'
                                ? 'TODO'
                                : 'COMPLETED',
                          })
                        }
                      >
                        {task.status === 'COMPLETED' ? '✓' : ''}
                      </button>
                    )}
                    <div className="task-title">
                      {view !== 'trash' ? (
                        <button
                          className={
                            task.status === 'COMPLETED' ? 'completed-title' : ''
                          }
                          onClick={() => setEditor({ task })}
                        >
                          {task.title}
                        </button>
                      ) : (
                        <strong>{task.title}</strong>
                      )}
                      <small>
                        {
                          lists.data?.find((list) => list.id === task.list_id)
                            ?.name
                        }{' '}
                        {task.checklist.length > 0 &&
                          `· ${task.checklist.filter((item) => item.completed).length}/${task.checklist.length} checklist`}
                      </small>
                    </div>
                    <span
                      className={`priority priority-${task.priority.toLowerCase()}`}
                    >
                      {task.priority.toLowerCase()}
                    </span>
                    <span className="task-date">
                      {task.due_date || 'No date'}
                    </span>
                    <span className="status-pill">
                      {statusLabel[task.status]}
                    </span>
                    {view === 'trash' ? (
                      <div className="actions">
                        <button
                          disabled={pending}
                          onClick={() =>
                            mutate(`/tasks/${task.id}/restore`, 'POST', {
                              confirmed: true,
                              version: task.version,
                            })
                          }
                        >
                          Restore
                        </button>
                        <button
                          className="danger-text"
                          disabled={pending}
                          onClick={() =>
                            confirm(
                              `Permanently delete “${task.title}”?`,
                              async () => {
                                await mutate(
                                  `/tasks/${task.id}/permanent`,
                                  'DELETE',
                                  { confirmed: true, version: task.version },
                                );
                              },
                            )
                          }
                        >
                          Delete permanently
                        </button>
                      </div>
                    ) : (
                      <button
                        disabled={pending}
                        aria-label={`Delete ${task.title}`}
                        onClick={() =>
                          confirm(
                            `Move “${task.title}” to Trash? You can restore it within 30 days.`,
                            async () => {
                              await mutate(`/tasks/${task.id}`, 'DELETE', {
                                confirmed: true,
                                version: task.version,
                              });
                            },
                          )
                        }
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </article>
                ))}
              </div>
            )}
            <div className="pagination">
              <span>
                Page {page} · {tasks.data?.total ?? 0} tasks
              </span>
              <button
                disabled={page === 1 || tasks.isFetching}
                onClick={() => {
                  setPage(page - 1);
                  setSelected([]);
                }}
              >
                Previous
              </button>
              <button
                disabled={
                  !tasks.data ||
                  page * tasks.data.page_size >= tasks.data.total ||
                  tasks.isFetching
                }
                onClick={() => {
                  setPage(page + 1);
                  setSelected([]);
                }}
              >
                Next
              </button>
            </div>
          </section>
        )}
        {view === 'calendar' && (
          <CalendarView open={(task) => setEditor({ task })} />
        )}
        {view === 'reports' && <Reports timezone={account.timezone} />}
        {view === 'notifications' && (
          <Notifications open={(task) => setEditor({ task })} />
        )}
        {view === 'data' && <Portability changed={changed} />}
        {view === 'admin' && <AdminAccounts confirm={confirm} />}
        {view === 'settings' && (
          <Settings
            account={account}
            changed={changed}
            signedOut={signedOut}
            confirm={confirm}
          />
        )}
        <footer>
          Room for your next good idea.{' '}
          <span>TaskTrack · {account.timezone}</span>
        </footer>
      </main>
      {editor && (
        <TaskEditor
          task={editor.task}
          lists={lists.data || []}
          tags={tags.data || []}
          close={() => setEditor(null)}
          saved={changed}
        />
      )}
      {manage && (
        <Dialog
          title={`${manage.id ? 'Rename' : 'Create'} ${manage.kind}`}
          close={() => {
            if (!pending) setManage(null);
          }}
        >
          <form onSubmit={manageSubmit}>
            <Field label="Name">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={manage.kind === 'list' ? 100 : 40}
                autoFocus
              />
            </Field>
            <div className="actions">
              <button
                type="button"
                disabled={pending}
                onClick={() => setManage(null)}
              >
                Cancel
              </button>
              <button className="primary" disabled={pending}>
                Save {manage.kind}
              </button>
            </div>
            {message && <p role="status">{message}</p>}
          </form>
        </Dialog>
      )}
      {confirmation && (
        <Dialog
          title="Confirm action"
          close={() => {
            if (!pending) setConfirmation(null);
          }}
        >
          <p>{confirmation.message}</p>
          <div className="actions">
            <button disabled={pending} onClick={() => setConfirmation(null)}>
              Cancel
            </button>
            <button
              className="danger"
              disabled={pending}
              onClick={async () => {
                setPending(true);
                try {
                  await confirmation.action();
                  setConfirmation(null);
                } catch (error) {
                  setMessage((error as Error).message);
                  setConfirmation(null);
                } finally {
                  setPending(false);
                }
              }}
            >
              Confirm
            </button>
          </div>
        </Dialog>
      )}
    </div>
  );
}

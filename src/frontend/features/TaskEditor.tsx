import { useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  request,
  taskInput,
  statusLabel,
  type Task,
  type TaskInput,
  type TaskList,
  type Tag,
  type Status,
  type Priority,
} from '../api/client';
import { Dialog, Field } from '../components/Dialog';

export function TaskEditor({
  task,
  lists,
  tags,
  close,
  saved,
}: {
  task: Task | null;
  lists: TaskList[];
  tags: Tag[];
  close: () => void;
  saved: () => void;
}) {
  const [form, setForm] = useState<TaskInput>(
    task
      ? taskInput(task)
      : {
          list_id: lists[0]?.id || '',
          title: '',
          description: '',
          due_date: null,
          priority: 'MEDIUM',
          status: 'TODO',
          checklist: [],
          tag_ids: [],
        },
  );
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const patch = (value: Partial<TaskInput>) =>
    setForm((old) => ({ ...old, ...value }));
  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError('');
    try {
      await request(
        task ? `/tasks/${task.id}` : '/tasks',
        task ? 'PUT' : 'POST',
        task ? { ...form, version: task.version } : form,
      );
      saved();
      close();
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setPending(false);
    }
  }
  return (
    <Dialog
      title={task ? 'Task details' : 'Create a task'}
      close={() => {
        if (!pending) close();
      }}
    >
      <form onSubmit={submit}>
        <fieldset disabled={pending}>
          <Field label="Title">
            <input
              value={form.title}
              onChange={(e) => patch({ title: e.target.value })}
              required
              maxLength={200}
              autoFocus
            />
          </Field>
          <Field label="List">
            <select
              value={form.list_id}
              onChange={(e) => patch({ list_id: e.target.value })}
              required
            >
              {lists.map((list) => (
                <option key={list.id} value={list.id}>
                  {list.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Description">
            <textarea
              value={form.description}
              onChange={(e) => patch({ description: e.target.value })}
              maxLength={5000}
              rows={3}
            />
          </Field>
          <div className="form-grid">
            <Field label="Due date (optional)">
              <input
                type="date"
                value={form.due_date || ''}
                onChange={(e) => patch({ due_date: e.target.value || null })}
              />
            </Field>
            <Field label="Priority">
              <select
                value={form.priority}
                onChange={(e) =>
                  patch({ priority: e.target.value as Priority })
                }
              >
                {['LOW', 'MEDIUM', 'HIGH'].map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </Field>
            <Field label="Status">
              <select
                value={form.status}
                onChange={(e) => patch({ status: e.target.value as Status })}
              >
                {Object.entries(statusLabel).map(([key, name]) => (
                  <option key={key} value={key}>
                    {name}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <h3>Checklist</h3>
          {form.checklist.map((item, index) => (
            <div className="checklist-row" key={index}>
              <input
                type="checkbox"
                aria-label={`Complete checklist item ${index + 1}`}
                checked={item.completed}
                onChange={(e) =>
                  patch({
                    checklist: form.checklist.map((value, i) =>
                      i === index
                        ? { ...value, completed: e.target.checked }
                        : value,
                    ),
                  })
                }
              />
              <input
                aria-label={`Checklist item ${index + 1}`}
                value={item.text}
                required
                maxLength={200}
                onChange={(e) =>
                  patch({
                    checklist: form.checklist.map((value, i) =>
                      i === index ? { ...value, text: e.target.value } : value,
                    ),
                  })
                }
              />
              <button
                type="button"
                disabled={index === 0}
                aria-label={`Move item ${index + 1} up`}
                onClick={() => {
                  const items = [...form.checklist];
                  [items[index - 1], items[index]] = [
                    items[index],
                    items[index - 1],
                  ];
                  patch({ checklist: items });
                }}
              >
                ↑
              </button>
              <button
                type="button"
                aria-label={`Delete checklist item ${index + 1}`}
                onClick={() =>
                  patch({
                    checklist: form.checklist.filter((_, i) => i !== index),
                  })
                }
              >
                ×
              </button>
            </div>
          ))}
          <button
            type="button"
            disabled={form.checklist.length >= 100}
            onClick={() =>
              patch({
                checklist: [...form.checklist, { text: '', completed: false }],
              })
            }
          >
            + Add checklist item
          </button>
          {tags.length > 0 && (
            <fieldset className="tag-options">
              <legend>Tags</legend>
              {tags.map((tag) => (
                <label key={tag.id}>
                  <input
                    type="checkbox"
                    checked={form.tag_ids.includes(tag.id)}
                    onChange={(e) =>
                      patch({
                        tag_ids: e.target.checked
                          ? [...form.tag_ids, tag.id]
                          : form.tag_ids.filter((id) => id !== tag.id),
                      })
                    }
                  />
                  {tag.name}
                </label>
              ))}
            </fieldset>
          )}
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <div className="actions">
            <button type="button" onClick={close}>
              Cancel
            </button>
            <button type="submit" className="primary">
              {pending ? 'Saving…' : 'Save task'}
            </button>
          </div>
        </fieldset>
      </form>
      {task && <TaskSchedule task={task} />}
    </Dialog>
  );
}

function TaskSchedule({ task }: { task: Task }) {
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  const [frequency, setFrequency] = useState('weekly');
  const [start, setStart] = useState(task.due_date || '');
  const [end, setEnd] = useState('');
  const [reminder, setReminder] = useState('');
  const [email, setEmail] = useState(false);
  type Schedule = {
    recurrence: { frequency: string; next_date: string } | null;
    reminders: {
      id: string;
      scheduled_at: string;
      delivered_at: string | null;
    }[];
  };
  const schedule = useQuery({
    queryKey: ['schedule', task.id],
    queryFn: () => request<Schedule>(`/tasks/${task.id}/schedule`),
  });
  const history = useQuery({
    queryKey: ['activity', task.id],
    queryFn: () =>
      request<{ id: string; event: string; occurred_at: string }[]>(
        `/tasks/${task.id}/activity`,
      ),
  });
  async function act(path: string, method: string, data?: unknown) {
    setPending(true);
    setMessage('');
    try {
      await request(path, method, data);
      await schedule.refetch();
      await history.refetch();
      setMessage('Schedule updated.');
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="schedule">
      <h3>Schedules & history</h3>
      {schedule.error && <p role="alert">{schedule.error.message}</p>}
      {schedule.data?.recurrence ? (
        <p>
          Repeats {schedule.data.recurrence.frequency}; next occurrence{' '}
          {schedule.data.recurrence.next_date}.{' '}
          <button
            disabled={pending}
            onClick={() => act(`/tasks/${task.id}/recurrence`, 'DELETE')}
          >
            Remove recurrence
          </button>
        </p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            act(`/tasks/${task.id}/recurrence`, 'PUT', {
              frequency,
              start,
              end_date: end || null,
            });
          }}
        >
          <fieldset disabled={pending}>
            <div className="form-grid">
              <Field label="Repeat">
                <select
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value)}
                >
                  <option>daily</option>
                  <option>weekly</option>
                  <option>monthly</option>
                </select>
              </Field>
              <Field label="First generated date">
                <input
                  type="date"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                  required
                />
              </Field>
              <Field label="End date (optional)">
                <input
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                />
              </Field>
            </div>
            <button>Save recurrence</button>
          </fieldset>
        </form>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          act(`/tasks/${task.id}/reminders`, 'POST', {
            scheduled_at: reminder,
            email,
          });
        }}
      >
        <fieldset disabled={pending}>
          <Field label="Reminder time (ISO date/time in your account timezone; include an offset for ambiguous DST times)">
            <input
              value={reminder}
              onChange={(e) => setReminder(e.target.value)}
              placeholder="2026-11-01T09:00:00-05:00"
              required
            />
          </Field>
          <label>
            <input
              type="checkbox"
              checked={email}
              onChange={(e) => setEmail(e.target.checked)}
            />{' '}
            Also send email (enable in settings)
          </label>
          <button>Schedule reminder</button>
        </fieldset>
      </form>
      {schedule.data?.reminders.map((item) => (
        <p key={item.id}>
          {new Date(item.scheduled_at).toLocaleString()} ·{' '}
          {item.delivered_at ? 'Processed' : 'Scheduled'}{' '}
          <button
            disabled={pending}
            onClick={() => act(`/reminders/${item.id}`, 'DELETE')}
          >
            Cancel reminder
          </button>
        </p>
      ))}
      {message && <p role="status">{message}</p>}
      <details>
        <summary>Activity history</summary>
        {history.error && <p role="alert">{history.error.message}</p>}
        <ol>
          {history.data?.map((item) => (
            <li key={item.id}>
              {item.event.replaceAll('_', ' ')} ·{' '}
              {new Date(item.occurred_at).toLocaleString()}
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}

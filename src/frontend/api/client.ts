let csrfToken = '';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function request<T>(
  path: string,
  method = 'GET',
  data?: unknown,
): Promise<T> {
  if (method !== 'GET' && !csrfToken) {
    const response = await fetch('/api/auth/csrf', {
      credentials: 'same-origin',
    });
    if (!response.ok)
      throw new Error('Cannot connect to TaskTrack. Try again.');
    csrfToken = (await response.json()).token;
  }
  const response = await fetch(`/api${path}`, {
    method,
    credentials: 'same-origin',
    headers: {
      ...(data === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(method === 'GET' ? {} : { 'X-CSRF-Token': csrfToken }),
    },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 403 && String(body.detail).includes('CSRF'))
      csrfToken = '';
    const fields = body.fields
      ?.map(
        (field: { field: string; message: string }) =>
          `${field.field}: ${field.message}`,
      )
      .join('; ');
    throw new ApiError(
      response.status,
      fields || body.detail || 'The request failed. Try again.',
    );
  }
  return body as T;
}

export type Account = {
  id: string;
  email: string;
  role: 'USER' | 'ADMIN';
  active: boolean;
  timezone: string;
  email_reminders: boolean;
};
export type TaskList = { id: string; name: string; version: number };
export type Tag = { id: string; name: string };
export type Status = 'TODO' | 'IN_PROGRESS' | 'COMPLETED';
export type Priority = 'LOW' | 'MEDIUM' | 'HIGH';
export type ChecklistItem = { text: string; completed: boolean };
export type TaskInput = {
  list_id: string;
  title: string;
  description: string;
  due_date: string | null;
  status: Status;
  priority: Priority;
  checklist: ChecklistItem[];
  tag_ids: string[];
};
export type Task = TaskInput & {
  id: string;
  version: number;
  created_at: string;
  completed_at: string | null;
  deleted_at: string | null;
  purge_after: string | null;
};
export type TaskPage = {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
};
export type Dashboard = {
  today: number;
  upcoming: number;
  overdue: number;
  status: Record<Status, number>;
};
export const statusLabel = {
  TODO: 'To Do',
  IN_PROGRESS: 'In Progress',
  COMPLETED: 'Completed',
};

export function taskInput(task: Task): TaskInput {
  const {
    list_id,
    title,
    description,
    due_date,
    status,
    priority,
    checklist,
    tag_ids,
  } = task;
  return {
    list_id,
    title,
    description,
    due_date,
    status,
    priority,
    checklist,
    tag_ids,
  };
}

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Auth } from '../../src/frontend/features/Auth';
import { TaskEditor } from '../../src/frontend/features/TaskEditor';
import { request } from '../../src/frontend/api/client';

vi.mock('../../src/frontend/api/client', async () => ({
  ...(await vi.importActual('../../src/frontend/api/client')),
  request: vi.fn(),
}));
const api = vi.mocked(request);
beforeEach(() => {
  vi.clearAllMocks();
  history.replaceState(null, '', '/');
  api.mockResolvedValue({});
});

describe('Account controls', () => {
  it('submits credentials without trimming the password', async () => {
    const done = vi.fn();
    const user = userEvent.setup();
    render(<Auth done={done} />);
    await user.type(screen.getByLabelText('Email'), 'student@example.com');
    await user.type(
      screen.getByLabelText('Password', { exact: true }),
      '  spaces are intentional  ',
    );
    await user.click(screen.getByRole('button', { name: 'Log in' }));
    await waitFor(() => expect(done).toHaveBeenCalledOnce());
    expect(api).toHaveBeenCalledWith('/auth/login', 'POST', {
      email: 'student@example.com',
      password: '  spaces are intentional  ',
    });
  });
  it('shows errors and allows retry', async () => {
    api.mockRejectedValueOnce(new Error('Invalid email or password'));
    const user = userEvent.setup();
    render(<Auth done={vi.fn()} />);
    await user.type(screen.getByLabelText('Email'), 'student@example.com');
    await user.type(
      screen.getByLabelText('Password', { exact: true }),
      'wrong',
    );
    await user.click(screen.getByRole('button', { name: 'Log in' }));
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Invalid email or password',
    );
    expect(screen.getByRole('button', { name: 'Log in' })).toBeEnabled();
  });
  it('blocks short registration passwords with browser validation', async () => {
    const user = userEvent.setup();
    render(<Auth done={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: 'Create account' }));
    expect(screen.getByLabelText('Password', { exact: true })).toHaveAttribute(
      'minlength',
      '12',
    );
    expect(screen.getByLabelText('Email')).toBeRequired();
  });
  it('uses the verification fragment and removes it from the URL', async () => {
    history.replaceState(null, '', '/#verify=verification-secret');
    const user = userEvent.setup();
    render(<Auth done={vi.fn()} />);
    expect(location.hash).toBe('');
    await user.click(screen.getByRole('button', { name: 'Verify email' }));
    expect(api).toHaveBeenCalledWith('/auth/verify', 'POST', {
      token: 'verification-secret',
    });
  });
});

describe('Task form controls', () => {
  function form() {
    const close = vi.fn(),
      saved = vi.fn();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <TaskEditor
          task={null}
          lists={[{ id: 'list-1', name: 'School', version: 1 }]}
          tags={[{ id: 'tag-1', name: 'Exam' }]}
          close={close}
          saved={saved}
        />
      </QueryClientProvider>,
    );
    return { close, saved };
  }
  it('saves title, list, date, priority, status, tag, checklist and reordering', async () => {
    const { saved } = form();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Title'), 'Assignment');
    await user.type(screen.getByLabelText('Due date (optional)'), '2026-10-25');
    await user.selectOptions(screen.getByLabelText('Priority'), 'HIGH');
    await user.selectOptions(screen.getByLabelText('Status'), 'IN_PROGRESS');
    await user.click(screen.getByLabelText('Exam'));
    await user.click(
      screen.getByRole('button', { name: '+ Add checklist item' }),
    );
    await user.type(
      screen.getByLabelText('Checklist item 1', { exact: true }),
      'First',
    );
    await user.click(
      screen.getByRole('button', { name: '+ Add checklist item' }),
    );
    await user.type(
      screen.getByLabelText('Checklist item 2', { exact: true }),
      'Second',
    );
    await user.click(screen.getByRole('button', { name: 'Move item 2 up' }));
    await user.click(screen.getByLabelText('Complete checklist item 1'));
    await user.click(screen.getByRole('button', { name: 'Save task' }));
    await waitFor(() => expect(saved).toHaveBeenCalledOnce());
    expect(api).toHaveBeenCalledWith(
      '/tasks',
      'POST',
      expect.objectContaining({
        title: 'Assignment',
        due_date: '2026-10-25',
        priority: 'HIGH',
        status: 'IN_PROGRESS',
        tag_ids: ['tag-1'],
        checklist: [
          { text: 'Second', completed: true },
          { text: 'First', completed: false },
        ],
      }),
    );
  });
  it('shows persistence errors without closing the editor', async () => {
    api.mockRejectedValueOnce(new Error('Storage is unavailable'));
    const { close } = form();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Title'), 'Keep my input');
    await user.click(screen.getByRole('button', { name: 'Save task' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Storage is unavailable',
    );
    expect(close).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Title')).toHaveValue('Keep my input');
  });
  it('cancels without writing and supports removing checklist items', async () => {
    const { close } = form();
    const user = userEvent.setup();
    await user.click(
      screen.getByRole('button', { name: '+ Add checklist item' }),
    );
    await user.click(
      screen.getByRole('button', { name: 'Delete checklist item 1' }),
    );
    expect(
      screen.queryByLabelText('Checklist item 1', { exact: true }),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(close).toHaveBeenCalledOnce();
    expect(api).not.toHaveBeenCalled();
  });
});

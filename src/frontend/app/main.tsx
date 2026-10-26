import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { ApiError, request, type Account } from '../api/client';
import { Auth } from '../features/Auth';
import { Workspace } from '../routes/Workspace';
import './styles.css';
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, staleTime: 10000, refetchOnWindowFocus: false },
  },
});

function App() {
  const cache = useQueryClient();
  const account = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        return await request<Account>('/me');
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
  });
  if (account.isPending)
    return (
      <main className="loading" role="status">
        Opening TaskTrack…
      </main>
    );
  if (account.error)
    return (
      <main className="loading">
        <h1>TaskTrack can’t connect</h1>
        <p role="alert">{account.error.message}</p>
        <button onClick={() => account.refetch()}>Try again</button>
      </main>
    );
  if (!account.data)
    return <Auth done={() => cache.invalidateQueries({ queryKey: ['me'] })} />;
  return (
    <Workspace
      account={account.data}
      signedOut={() => {
        void cache.cancelQueries();
        cache.removeQueries({
          predicate: (query) => query.queryKey[0] !== 'me',
        });
        cache.setQueryData(['me'], null);
      }}
    />
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);

import type { PromptsResponse, PromptTemplate, Task, TaskCreate } from '@/types';

const API_BASE = '/api';

export async function getPrompts(): Promise<PromptsResponse> {
  const response = await fetch(`${API_BASE}/prompts`);
  if (!response.ok) throw new Error('Failed to fetch prompts');
  return response.json();
}

export async function getPrompt(id: string): Promise<PromptTemplate> {
  const response = await fetch(`${API_BASE}/prompts/${id}`);
  if (!response.ok) throw new Error('Failed to fetch prompt');
  return response.json();
}

export async function createTask(task: TaskCreate): Promise<Task> {
  const response = await fetch(`${API_BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(task),
  });
  if (!response.ok) throw new Error('Failed to create task');
  return response.json();
}

export async function getTask(id: string): Promise<Task> {
  const response = await fetch(`${API_BASE}/tasks/${id}`);
  if (!response.ok) throw new Error('Failed to fetch task');
  return response.json();
}

export function streamTask(
  taskId: string,
  onMessage: (chunk: string) => void,
  onDone: () => void,
  onError: (error: string) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/stream/${taskId}`);

  eventSource.addEventListener('message', (event) => {
    onMessage(event.data);
  });

  eventSource.addEventListener('done', () => {
    eventSource.close();
    onDone();
  });

  eventSource.addEventListener('error', () => {
    eventSource.close();
    onError('Stream error');
  });

  return () => eventSource.close();
}

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
  const eventSource = new EventSource(`${API_BASE}/tasks/stream/${taskId}`);
  let connected = false;
  let errorCount = 0;

  eventSource.addEventListener('open', () => {
    connected = true;
    errorCount = 0;
  });

  eventSource.addEventListener('message', (event) => {
    connected = true;
    onMessage(event.data);
  });

  eventSource.addEventListener('done', () => {
    eventSource.close();
    onDone();
  });

  eventSource.addEventListener('error', () => {
    if (connected) {
      // 已连接后出错，允许重试几次
      errorCount++;
      if (errorCount > 3) {
        eventSource.close();
        onError('SSE 连接中断');
      }
    }
    // 未连接时的 error 是 EventSource 自动重试过程，不处理
  });

  // 30 秒超时保护
  const timeout = setTimeout(() => {
    if (!connected) {
      eventSource.close();
      onError('SSE 连接超时');
    }
  }, 30000);

  return () => {
    clearTimeout(timeout);
    eventSource.close();
  };
}

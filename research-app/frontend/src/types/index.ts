export interface PromptTemplate {
  id: string;
  name: string;
  category: 'bull' | 'bear' | 'oscillation';
  keywords: string[];
  prompt: string;
  variables: string[];
  description: string;
  created_at: string;
  updated_at: string;
}

export interface CategoryInfo {
  name: string;
  icon: string;
  color: string;
}

export interface PromptsResponse {
  version: string;
  metadata: Record<string, unknown>;
  categories: Record<string, {
    info: CategoryInfo;
    templates: PromptTemplate[];
  }>;
}

export interface Task {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  prompt_id: string;
  result: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface TaskCreate {
  prompt_id: string;
  variables: Record<string, string>;
  model?: string;
}

export interface HistoryItem {
  task: Task;
  promptName: string;
  category: string;
}

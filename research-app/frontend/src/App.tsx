import { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import MarketTabs from './components/MarketTabs';
import PromptCard from './components/PromptCard';
import ResultPanel from './components/ResultPanel';
import HistoryDrawer from './components/HistoryDrawer';
import { getPrompts, createTask, streamTask } from '@/lib/api';
import { saveHistory, loadHistory } from '@/lib/utils';
import type { PromptsResponse, PromptTemplate, Task, HistoryItem } from '@/types';

const CATEGORY_COLORS: Record<string, string> = {
  bull: 'bg-red-100 text-red-700',
  bear: 'bg-green-100 text-green-700',
  oscillation: 'bg-amber-100 text-amber-700',
};

export default function App() {
  const [activeTab, setActiveTab] = useState('bull');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [promptsData, setPromptsData] = useState<PromptsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState('');
  const [history, setHistory] = useState<HistoryItem[]>(loadHistory());

  useEffect(() => {
    getPrompts().then(data => {
      setPromptsData(data);
      setLoading(false);
    });
  }, []);

  const handleExecute = useCallback(async (promptId: string, variables: Record<string, string>) => {
    try {
      const task = await createTask({ prompt_id: promptId, variables });
      setActiveTask(task);
      setStreaming(true);
      setStreamedContent('');

      const prompt = promptsData?.categories[activeTab]?.templates.find((t: PromptTemplate) => t.id === promptId);

      streamTask(
        task.id,
        (chunk) => setStreamedContent(prev => prev + chunk),
        () => {
          setStreaming(false);
          fetch(`/api/tasks/${task.id}`)
            .then(r => r.json())
            .then((finalTask: Task) => {
              setActiveTask(finalTask);
              if (prompt) {
                const newHistory: HistoryItem = {
                  task: finalTask,
                  promptName: prompt.name,
                  category: activeTab,
                };
                const updated = [newHistory, ...history].slice(0, 50);
                setHistory(updated);
                saveHistory(updated);
              }
            });
        },
        (error) => {
          setStreaming(false);
          console.error('Stream error:', error);
        }
      );
    } catch (error) {
      console.error('Execute error:', error);
    }
  }, [activeTab, promptsData, history]);

  const handleCloseResult = () => {
    setActiveTask(null);
    setStreamedContent('');
  };

  const handleSelectTask = (task: Task) => {
    setActiveTask(task);
    setStreamedContent(task.result || '');
    setHistoryOpen(false);
  };

  const handleClearHistory = () => {
    setHistory([]);
    saveHistory([]);
  };

  const currentTemplates = promptsData?.categories[activeTab]?.templates || [];

  return (
    <div className="min-h-screen bg-gray-50">
      <Header onHistoryClick={() => setHistoryOpen(true)} />
      <MarketTabs activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="px-6 pb-6 max-w-4xl mx-auto">
        {loading ? (
          <p className="text-center text-gray-500 py-8">加载中...</p>
        ) : (
          <div className="space-y-4">
            {currentTemplates.map((prompt) => (
              <PromptCard
                key={prompt.id}
                prompt={prompt}
                categoryColor={CATEGORY_COLORS[activeTab]}
                onExecute={handleExecute}
              />
            ))}
            {currentTemplates.length === 0 && (
              <p className="text-center text-gray-400 py-8">暂无该分类的提示词模板</p>
            )}
          </div>
        )}
      </main>

      <ResultPanel
        task={activeTask}
        streaming={streaming}
        streamedContent={streamedContent}
        onClose={handleCloseResult}
      />

      <HistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        history={history}
        onSelectTask={handleSelectTask}
        onClearHistory={handleClearHistory}
      />
    </div>
  );
}

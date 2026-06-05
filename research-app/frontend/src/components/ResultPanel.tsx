import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { X, Loader2 } from 'lucide-react';
import type { Task } from '@/types';

interface ResultPanelProps {
  task: Task | null;
  streaming: boolean;
  streamedContent: string;
  onClose: () => void;
}

export default function ResultPanel({ task, streaming, streamedContent, onClose }: ResultPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [streamedContent]);

  if (!task) return null;

  const displayContent = streaming ? streamedContent : (task.result || '');
  const hasError = task.status === 'failed';

  return (
    <div className="fixed inset-x-0 bottom-0 bg-white border-t shadow-lg z-50 max-h-[50vh] flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b bg-gray-50">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-sm">执行结果</h3>
          {streaming && (
            <span className="inline-flex items-center gap-1 text-xs text-blue-600">
              <Loader2 className="h-3 w-3 animate-spin" />
              生成中...
            </span>
          )}
          {task.status === 'completed' && <span className="text-xs text-green-600">已完成</span>}
          {hasError && <span className="text-xs text-red-600">失败</span>}
        </div>
        <button onClick={onClose} className="p-1 hover:bg-gray-200 rounded">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
        {hasError ? (
          <div className="text-red-600 text-sm">{task.error}</div>
        ) : displayContent ? (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{displayContent}</ReactMarkdown>
          </div>
        ) : streaming ? (
          <div className="text-gray-400 text-sm">等待响应...</div>
        ) : (
          <div className="text-gray-400 text-sm">暂无结果</div>
        )}
      </div>
    </div>
  );
}

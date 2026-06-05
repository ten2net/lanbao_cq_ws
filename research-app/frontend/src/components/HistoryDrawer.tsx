import { X, Clock, Trash2 } from 'lucide-react';
import { cn, formatDate } from '@/lib/utils';
import type { HistoryItem, Task } from '@/types';

interface HistoryDrawerProps {
  open: boolean;
  onClose: () => void;
  history: HistoryItem[];
  onSelectTask: (task: Task) => void;
  onClearHistory: () => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  bull: '牛市',
  bear: '熊市',
  oscillation: '震荡',
};

const CATEGORY_COLORS: Record<string, string> = {
  bull: 'text-red-600 bg-red-50',
  bear: 'text-green-600 bg-green-50',
  oscillation: 'text-amber-600 bg-amber-50',
};

export default function HistoryDrawer({ open, onClose, history, onSelectTask, onClearHistory }: HistoryDrawerProps) {
  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-50" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-gray-500" />
            <h2 className="font-semibold">历史记录</h2>
            <span className="text-xs text-gray-400">({history.length})</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onClearHistory} className="p-1 text-gray-400 hover:text-red-500 transition-colors" title="清空历史">
              <Trash2 className="h-4 w-4" />
            </button>
            <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {history.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Clock className="h-8 w-8 mb-2" />
              <p>暂无历史记录</p>
            </div>
          ) : (
            <div className="divide-y">
              {history.map((item, index) => (
                <button
                  key={`${item.task.id}-${index}`}
                  onClick={() => onSelectTask(item.task)}
                  className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm truncate">{item.promptName}</span>
                    <span className={cn('text-xs px-2 py-0.5 rounded-full', CATEGORY_COLORS[item.category])}>
                      {CATEGORY_LABELS[item.category]}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <span>{formatDate(item.task.created_at)}</span>
                    <span>·</span>
                    <span className={cn(
                      item.task.status === 'completed' ? 'text-green-500' :
                      item.task.status === 'failed' ? 'text-red-500' :
                      'text-blue-500'
                    )}>
                      {item.task.status === 'completed' ? '已完成' :
                       item.task.status === 'failed' ? '失败' :
                       item.task.status === 'running' ? '进行中' : '等待中'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

import { TrendingUp, History } from 'lucide-react';

interface HeaderProps {
  onHistoryClick: () => void;
}

export default function Header({ onHistoryClick }: HeaderProps) {
  return (
    <header className="border-b bg-white px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <TrendingUp className="h-6 w-6 text-primary" />
        <h1 className="text-xl font-bold">揽宝智能投研</h1>
      </div>
      <button
        onClick={onHistoryClick}
        className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md hover:bg-gray-100 transition-colors"
      >
        <History className="h-4 w-4" />
        历史记录
      </button>
    </header>
  );
}

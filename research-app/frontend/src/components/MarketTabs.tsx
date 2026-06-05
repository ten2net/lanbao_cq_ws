import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

const TABS = [
  { key: 'bull' as const, label: '牛市环境', icon: TrendingUp, color: 'text-red-500', active: 'bg-red-100 border-red-300' },
  { key: 'bear' as const, label: '熊市环境', icon: TrendingDown, color: 'text-green-500', active: 'bg-green-100 border-green-300' },
  { key: 'oscillation' as const, label: '震荡市', icon: Activity, color: 'text-amber-500', active: 'bg-amber-100 border-amber-300' },
];

interface MarketTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function MarketTabs({ activeTab, onTabChange }: MarketTabsProps) {
  return (
    <div className="flex gap-3 px-6 py-4">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.key;
        return (
          <button
            key={tab.key}
            onClick={() => onTabChange(tab.key)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg border-2 font-medium transition-all',
              isActive ? `${tab.active} ${tab.color}` : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
            )}
          >
            <Icon className="h-5 w-5" />
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

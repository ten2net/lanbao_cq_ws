import { useState } from 'react';
import { Play, Edit, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PromptTemplate } from '@/types';

interface PromptCardProps {
  prompt: PromptTemplate;
  categoryColor: string;
  onExecute: (promptId: string, variables: Record<string, string>) => void;
}

export default function PromptCard({ prompt, categoryColor, onExecute }: PromptCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [isExecuting, setIsExecuting] = useState(false);

  const handleExecute = async () => {
    setIsExecuting(true);
    try {
      await onExecute(prompt.id, variableValues);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow">
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900">{prompt.name}</h3>
            <div className="flex flex-wrap gap-1 mt-2">
              {prompt.keywords.map((kw) => (
                <span key={kw} className={cn('px-2 py-0.5 text-xs rounded-full font-medium', categoryColor)}>{kw}</span>
              ))}
            </div>
            <p className="text-sm text-gray-500 mt-2">{prompt.description}</p>
          </div>
          <div className="flex gap-2 ml-4">
            <button
              onClick={handleExecute}
              disabled={isExecuting}
              className="inline-flex items-center gap-1 px-3 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              {isExecuting ? '执行中...' : '执行'}
            </button>
            <button className="inline-flex items-center gap-1 px-3 py-2 border rounded-md text-sm font-medium hover:bg-gray-50">
              <Edit className="h-4 w-4" />
            </button>
          </div>
        </div>

        {prompt.variables.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-3">
            {prompt.variables.map((varName) => (
              <div key={varName} className="flex items-center gap-2">
                <label className="text-sm text-gray-600">{varName}:</label>
                <input
                  type="text"
                  value={variableValues[varName] || ''}
                  onChange={(e) => setVariableValues(prev => ({ ...prev, [varName]: e.target.value }))}
                  className="px-2 py-1 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder={`输入${varName}`}
                />
              </div>
            ))}
          </div>
        )}

        <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-1 mt-3 text-sm text-gray-500 hover:text-gray-700">
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          {expanded ? '收起' : '查看提示词'}
        </button>

        {expanded && (
          <div className="mt-3 p-3 bg-gray-50 rounded-md text-sm text-gray-700 whitespace-pre-wrap">{prompt.prompt}</div>
        )}
      </div>
    </div>
  );
}

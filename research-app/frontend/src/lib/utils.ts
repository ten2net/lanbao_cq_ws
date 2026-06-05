import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import type { HistoryItem } from "@/types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('zh-CN');
}

export function saveHistory(history: HistoryItem[]) {
  localStorage.setItem('research_history', JSON.stringify(history));
}

export function loadHistory(): HistoryItem[] {
  const stored = localStorage.getItem('research_history');
  return stored ? JSON.parse(stored) : [];
}

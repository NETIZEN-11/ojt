import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) {
    const sec = ms / 1000;
    return sec % 1 === 0 ? `${sec}s` : `${sec.toFixed(1)}s`;
  }
  const min = ms / 60000;
  return min % 1 === 0 ? `${min}m` : `${min.toFixed(1)}m`;
}

export function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case "critical":
      return "text-red-600 bg-red-50 border-red-200";
    case "high":
      return "text-orange-600 bg-orange-50 border-orange-200";
    case "medium":
      return "text-yellow-600 bg-yellow-50 border-yellow-200";
    case "low":
      return "text-blue-600 bg-blue-50 border-blue-200";
    default:
      return "text-gray-600 bg-gray-50 border-gray-200";
  }
}

export function getVerdictColor(verdict: string): string {
  switch (verdict) {
    case "PASS":
      return "text-green-600 bg-green-50 border-green-200";
    case "FAIL":
      return "text-red-600 bg-red-50 border-red-200";
    case "INCONCLUSIVE":
      return "text-yellow-600 bg-yellow-50 border-yellow-200";
    default:
      return "text-gray-600 bg-gray-50 border-gray-200";
  }
}

export function getStatusColor(status: string): string {
  switch (status) {
    case "completed":
      return "text-green-600 bg-green-50";
    case "failed":
      return "text-red-600 bg-red-50";
    case "running":
      return "text-blue-600 bg-blue-50";
    case "queued":
      return "text-gray-600 bg-gray-50";
    case "review_required":
      return "text-orange-600 bg-orange-50";
    default:
      return "text-gray-600 bg-gray-50";
  }
}
import { analyses } from './mockData';
import { apiClient } from './apiClient';

export async function listAnalyses() {
  return apiClient.listAnalyses();
}

export async function runAnalysis(payload) {
  return apiClient.runAnalysis(payload);
}

export function getAnalysisSummary() {
  return {
    total: analyses.length,
    completed: analyses.filter((item) => item.status === 'Complete').length,
    averageConfidence: Math.round(analyses.reduce((sum, item) => sum + item.confidence, 0) / analyses.length),
  };
}
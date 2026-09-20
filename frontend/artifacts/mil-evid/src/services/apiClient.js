import { analyses, evidence, sources } from './mockData';

const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
export const apiClient = {
  baseUrl,
  async listAnalyses() { return analyses; },
  async listEvidence() { return evidence; },
  async listSources() { return sources; },
  async runAnalysis(payload) { return { ...analyses[0], id: `AN-${Math.floor(1000 + Math.random() * 8999)}`, query: payload.query, perspectives: payload.perspectives, region: payload.region || 'Unspecified', status: 'Complete' }; },
};
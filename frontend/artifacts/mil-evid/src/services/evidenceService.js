import { evidence, sources } from './mockData';
import { apiClient } from './apiClient';

export async function listEvidence() {
  return apiClient.listEvidence();
}

export async function listSources() {
  return apiClient.listSources();
}

export function searchEvidence({ query = '', perspective = 'All', type = 'All', date = 'Any date' } = {}) {
  return evidence.filter((record) => {
    const haystack = `${record.title} ${record.source} ${record.fullText}`.toLowerCase();
    const dateMatch = date === 'Any date' || (date === '2025' ? record.date.startsWith('2025') : date === 'Last 90 days' ? record.date >= '2025-01-01' : record.date >= '2025-02-01');
    return haystack.includes(query.toLowerCase()) && (perspective === 'All' || record.perspective === perspective) && (type === 'All' || record.type === type) && dateMatch;
  });
}

export { sources };
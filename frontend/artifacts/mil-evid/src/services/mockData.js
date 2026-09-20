export const analyses = [
  { id: 'AN-0427', query: 'What is the likely operational posture around the Suwałki corridor?', perspectives: ['Operational', 'Geopolitical', 'Humanitarian'], region: 'Baltic region', period: 'Q1 2025', confidence: 78, status: 'Complete', evidenceCount: 24, timestamp: '2025-03-18T14:32:00Z' },
  { id: 'AN-0419', query: 'Assess maritime security implications of recent Red Sea incidents.', perspectives: ['Operational', 'Legal', 'Historical'], region: 'Red Sea', period: '2024–25', confidence: 71, status: 'Complete', evidenceCount: 31, timestamp: '2025-03-14T09:08:00Z' },
  { id: 'AN-0408', query: 'How have ceasefire monitoring patterns changed since 2022?', perspectives: ['Historical', 'Humanitarian'], region: 'Eastern Europe', period: '2022–25', confidence: 84, status: 'Complete', evidenceCount: 19, timestamp: '2025-03-08T16:11:00Z' },
  { id: 'AN-0397', query: 'Map reported logistics constraints affecting the northern theatre.', perspectives: ['Operational', 'Geopolitical'], region: 'Northern theatre', period: 'Feb 2025', confidence: 63, status: 'Review', evidenceCount: 15, timestamp: '2025-02-27T11:42:00Z' },
  { id: 'AN-0384', query: 'Identify precedents for protected humanitarian corridors.', perspectives: ['Legal', 'Historical'], region: 'Levant', period: '1990–2024', confidence: 89, status: 'Complete', evidenceCount: 28, timestamp: '2025-02-18T13:24:00Z' },
];

export const evidence = [
  { id: 'EV-1882', source: 'NATO StratCom', title: 'Regional Security Assessment: Baltic Approaches', perspective: 'Operational', date: '2025-03-17', relevance: 94, type: 'Assessment', fullText: 'The Suwałki corridor remains a critical connective tissue between allied territory and the Baltic states. Current indicators suggest increased surveillance activity and deliberate ambiguity in exercise signaling.', url: 'https://example.org/archive/ev-1882' },
  { id: 'EV-1876', source: 'OSCE Archive', title: 'Field Mission Weekly Brief — 11 March', perspective: 'Humanitarian', date: '2025-03-11', relevance: 88, type: 'Field report', fullText: 'Monitoring teams recorded restricted movement at three crossing points. Local authorities cited routine exercises; independent observers noted unusual night-time convoy activity.', url: 'https://example.org/archive/ev-1876' },
  { id: 'EV-1864', source: 'IISS', title: 'The Baltic Balance: Signals and Constraints', perspective: 'Geopolitical', date: '2025-03-05', relevance: 83, type: 'Analysis', fullText: 'Political signaling is calibrated to preserve room for de-escalation. Material readiness and public rhetoric should not be treated as interchangeable measures of intent.', url: 'https://example.org/archive/ev-1864' },
  { id: 'EV-1849', source: 'European Council on Foreign Relations', title: 'Deterrence Without Escalation', perspective: 'Legal', date: '2025-02-22', relevance: 79, type: 'Policy paper', fullText: 'Existing treaty commitments create a layered obligation to consult, but do not mechanically determine the proportionality of every response.', url: 'https://example.org/archive/ev-1849' },
  { id: 'EV-1820', source: 'US Army Heritage Center', title: 'Corridor Operations in Divided Terrain, 1944–1999', perspective: 'Historical', date: '2025-01-31', relevance: 73, type: 'Archive', fullText: 'Historical corridor crises show that logistical vulnerability often becomes strategically decisive before a formal change in force posture.', url: 'https://example.org/archive/ev-1820' },
  { id: 'EV-1798', source: 'Bellingcat Open Source', title: 'Geolocated Convoy Activity Near Suwałki', perspective: 'Operational', date: '2025-01-24', relevance: 68, type: 'OSINT', fullText: 'Open-source imagery places a sequence of heavy vehicles on approach roads over a four-day period. Identification confidence is moderate due to image quality.', url: 'https://example.org/archive/ev-1798' },
];

export const sources = [
  { name: 'SIPRI', category: 'Arms transfers', lastSync: '12 min ago', recordCount: '18,421', status: 'Connected' },
  { name: 'UCDP GED', category: 'Georeferenced events', lastSync: '24 min ago', recordCount: '9,804', status: 'Connected' },
  { name: 'UCDP Dyadic', category: 'Conflict relationships', lastSync: '2 hrs ago', recordCount: '6,217', status: 'Connected' },
  { name: 'ICRC', category: 'Humanitarian law', lastSync: 'Yesterday', recordCount: '42,091', status: 'Degraded' },
  { name: 'UN Peacemaker', category: 'Peace agreements', lastSync: '4 hrs ago', recordCount: '31,774', status: 'Connected' },
  { name: 'ACLED', category: 'Political violence', lastSync: '6 hrs ago', recordCount: '18,900', status: 'Connected' },
];

export const trend = [
  { month: 'Oct', analyses: 8, confidence: 71 }, { month: 'Nov', analyses: 12, confidence: 74 }, { month: 'Dec', analyses: 10, confidence: 69 }, { month: 'Jan', analyses: 16, confidence: 77 }, { month: 'Feb', analyses: 21, confidence: 75 }, { month: 'Mar', analyses: 27, confidence: 81 },
];

export const perspectiveDistribution = [
  { name: 'Operational', value: 34 }, { name: 'Geopolitical', value: 26 }, { name: 'Historical', value: 18 }, { name: 'Humanitarian', value: 13 }, { name: 'Legal', value: 9 },
];

export const claims = [
  { text: 'The corridor is experiencing elevated surveillance and readiness activity, but not an unambiguous pre-conflict posture.', status: 'Supported', confidence: 82, supporting: ['EV-1882', 'EV-1864'], contradicting: ['EV-1798'] },
  { text: 'Movement restrictions are creating a measurable, localized humanitarian burden.', status: 'Supported', confidence: 76, supporting: ['EV-1876'], contradicting: [] },
  { text: 'Current treaty obligations increase consultation pressure without prescribing a single operational response.', status: 'Contested', confidence: 61, supporting: ['EV-1849'], contradicting: ['EV-1864'] },
];

export const contradictions = [
  { claim: 'Interpretation of convoy activity', evidenceA: 'EV-1798', evidenceB: 'EV-1882', conflict: 'Open-source imagery suggests sustained logistics activity; the institutional assessment characterizes indicators as surveillance-led.', severity: 'Moderate' },
  { claim: 'Intent behind movement restrictions', evidenceA: 'EV-1876', evidenceB: 'EV-1864', conflict: 'Field monitors describe access constraints while regional analysis emphasizes calibrated signaling.', severity: 'Low' },
];

export const systemRecords = [
  { label: 'Application', detail: 'Frontend shell · local preview', status: 'Operational' },
  { label: 'Database', detail: 'Mock persistence · session ready', status: 'Operational' },
  { label: 'LLM', detail: 'Mock synthesis layer · 4 perspectives', status: 'Operational' },
  { label: 'BM25', detail: 'Lexical retrieval simulation', status: 'Operational' },
  { label: 'FAISS', detail: 'Vector index simulation · 126,307 records', status: 'Operational' },
  { label: 'Cross-Encoder', detail: 'Reranking simulation · 99.2% links verified', status: 'Degraded' },
];

export function getAnalysis(id) { return analyses.find((item) => item.id === id) || analyses[0]; }
export function getEvidence(id) { return evidence.find((item) => item.id === id) || evidence[0]; }
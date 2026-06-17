// Copy to: backend/src/services/mlClient.ts
import { env } from '../config/env';

export interface QueryRequest {
  message: string;
}

export interface Source {
  title: string;
  url?: string;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
}

export async function queryML(payload: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${env.ML_SERVICE_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = new Error(`ML service error: ${res.status}`) as Error & { statusCode: number };
    err.statusCode = 502;
    throw err;
  }

  return res.json() as Promise<QueryResponse>;
}

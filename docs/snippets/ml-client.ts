// Copy to: backend/src/services/mlClient.ts
import { env } from '../config/env';

export interface PredictRequest {
  input: string; // Replace with your actual input fields
}

export interface PredictResponse {
  result: unknown;
  confidence?: number;
}

export async function predict(payload: PredictRequest): Promise<PredictResponse> {
  const res = await fetch(`${env.ML_SERVICE_URL}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = new Error(`ML service error: ${res.status}`) as Error & { statusCode: number };
    err.statusCode = 502;
    throw err;
  }

  return res.json() as Promise<PredictResponse>;
}

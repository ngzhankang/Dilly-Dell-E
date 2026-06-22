import { Router } from 'express';
import { asyncHandler } from '../middleware/asyncHandler';
import { env } from '../config/env';

export const voiceRoutes = Router();

/**
 * POST /api/voice/sessions/start
 * Forward to ML service: POST /voice/sessions/start
 *
 * Body: { patient_id: string }
 */
voiceRoutes.post(
  '/sessions/start',
  asyncHandler(async (req, res) => {
    const response = await fetch(`${env.ML_SERVICE_URL}/voice/sessions/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body),
    });

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json(error);
    }

    const data = await response.json();
    res.json(data);
  })
);

/**
 * POST /api/voice/turn
 * Forward to ML service: POST /voice/turn
 *
 * Body: {
 *   session_id: string,
 *   patient_id: string,
 *   text: string  (transcribed user input)
 * }
 */
voiceRoutes.post(
  '/turn',
  asyncHandler(async (req, res) => {
    const response = await fetch(`${env.ML_SERVICE_URL}/voice/turn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body),
    });

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json(error);
    }

    const data = await response.json();
    res.json(data);
  })
);

/**
 * POST /api/voice/sessions/:id/end
 * Forward to ML service: POST /voice/sessions/{id}/end
 *
 * Closes a conversation session
 */
voiceRoutes.post(
  '/sessions/:id/end',
  asyncHandler(async (req, res) => {
    const response = await fetch(`${env.ML_SERVICE_URL}/voice/sessions/${req.params.id}/end`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json(error);
    }

    const data = await response.json();
    res.json(data);
  })
);

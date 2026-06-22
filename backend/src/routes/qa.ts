import { Router } from 'express';
import { asyncHandler } from '../middleware/asyncHandler';
import { env } from '../config/env';

export const qaRoutes = Router();

/**
 * POST /api/qa/check-response
 * Forward to ML service: POST /qa/check-response
 *
 * Body: {
 *   response: string,
 *   confidence: number (0.0-1.0),
 *   retrieved_sources: string[]
 * }
 */
qaRoutes.post(
  '/check-response',
  asyncHandler(async (req, res) => {
    const response = await fetch(`${env.ML_SERVICE_URL}/qa/check-response`, {
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
 * POST /api/qa/escalate
 * Forward to ML service: POST /qa/escalate
 *
 * Escalate low-confidence response to human review
 */
qaRoutes.post(
  '/escalate',
  asyncHandler(async (req, res) => {
    const response = await fetch(`${env.ML_SERVICE_URL}/qa/escalate`, {
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
 * POST /api/qa/log-interaction
 * Forward to ML service: POST /qa/log-interaction
 *
 * Log interaction for audit trail
 */
qaRoutes.post(
  '/log-interaction',
  asyncHandler(async (req, res) => {
    const response = await fetch(`${env.ML_SERVICE_URL}/qa/log-interaction`, {
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
 * GET /api/qa/reviews/pending
 * Forward to ML service: GET /qa/reviews/pending
 *
 * Get pending reviews for human reviewer dashboard
 */
qaRoutes.get(
  '/reviews/pending',
  asyncHandler(async (req, res) => {
    const limit = req.query.limit || '50';

    const response = await fetch(`${env.ML_SERVICE_URL}/qa/reviews/pending?limit=${limit}`, {
      method: 'GET',
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
 * GET /api/qa/reviews/:id
 * Forward to ML service: GET /qa/reviews/{id}
 *
 * Get a specific review item
 */
qaRoutes.get(
  '/reviews/:id',
  asyncHandler(async (req, res) => {
    const response = await fetch(`${env.ML_SERVICE_URL}/qa/reviews/${req.params.id}`, {
      method: 'GET',
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
 * POST /api/qa/reviews/:id/approve
 * Forward to ML service: POST /qa/reviews/{id}/approve
 *
 * Approve a review (accept LLM response)
 */
qaRoutes.post(
  '/reviews/:id/approve',
  asyncHandler(async (req, res) => {
    const response = await fetch(
      `${env.ML_SERVICE_URL}/qa/reviews/${req.params.id}/approve`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json(error);
    }

    const data = await response.json();
    res.json(data);
  })
);

/**
 * POST /api/qa/reviews/:id/reject
 * Forward to ML service: POST /qa/reviews/{id}/reject
 *
 * Reject a review
 */
qaRoutes.post(
  '/reviews/:id/reject',
  asyncHandler(async (req, res) => {
    const response = await fetch(
      `${env.ML_SERVICE_URL}/qa/reviews/${req.params.id}/reject`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json(error);
    }

    const data = await response.json();
    res.json(data);
  })
);

/**
 * POST /api/qa/reviews/:id/modify
 * Forward to ML service: POST /qa/reviews/{id}/modify
 *
 * Modify and approve a review (provide corrected response)
 */
qaRoutes.post(
  '/reviews/:id/modify',
  asyncHandler(async (req, res) => {
    const response = await fetch(
      `${env.ML_SERVICE_URL}/qa/reviews/${req.params.id}/modify`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json(error);
    }

    const data = await response.json();
    res.json(data);
  })
);

/**
 * GET /api/qa/reviews/stats
 * Forward to ML service: GET /qa/reviews/stats
 *
 * Get review queue statistics
 */
qaRoutes.get(
  '/reviews/stats',
  asyncHandler(async (req, res) => {
    const response = await fetch(`${env.ML_SERVICE_URL}/qa/reviews/stats`, {
      method: 'GET',
    });

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json(error);
    }

    const data = await response.json();
    res.json(data);
  })
);

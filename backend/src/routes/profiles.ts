import { Router } from 'express';
import { asyncHandler } from '../middleware/asyncHandler';
import { env } from '../config/env';

export const profileRoutes = Router();

/**
 * POST /api/profiles
 * Forward to ML service: POST /profiles
 *
 * Body: {
 *   agency_name: string,
 *   record: { name, dob, age, contact, emotion, problem_classes, special_case }
 * }
 */
profileRoutes.post(
  '/',
  asyncHandler(async (req, res) => {
    const response = await fetch(`${env.ML_SERVICE_URL}/profiles`, {
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
 * GET /api/profiles/:id
 * Forward to ML service: GET /profiles/{id}
 *
 * Returns: UnifiedProfile { patient_id, name, dob, age, contact, ... }
 */
profileRoutes.get(
  '/:id',
  asyncHandler(async (req, res) => {
    const response = await fetch(`${env.ML_SERVICE_URL}/profiles/${req.params.id}`, {
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
 * GET /api/profiles
 * Forward to ML service: GET /profiles (list all profiles)
 *
 * Query params: skip, limit
 */
profileRoutes.get(
  '/',
  asyncHandler(async (req, res) => {
    const skip = req.query.skip || '0';
    const limit = req.query.limit || '100';

    const response = await fetch(
      `${env.ML_SERVICE_URL}/profiles?skip=${skip}&limit=${limit}`,
      {
        method: 'GET',
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

import { Router } from 'express';
import { asyncHandler } from '../middleware/asyncHandler';
import { env } from '../config/env';

export const adapterRoutes = Router();

/**
 * POST /api/adapter/import
 * Forward to ML service: POST /adapter/import
 *
 * Form data:
 * - file: File (CSV/Excel/JSON/PDF)
 * - agency_name: string
 */
adapterRoutes.post(
  '/import',
  asyncHandler(async (req, res) => {
    // Proxy multipart form data to ML service
    const formData = new FormData();

    // Add file from request
    if (!req.file) {
      return res.status(400).json({ error: 'No file provided' });
    }
    formData.append('file', new Blob([new Uint8Array(req.file.buffer)]), req.file.originalname);
    formData.append('agency_name', req.body.agency_name || '');

    const response = await fetch(`${env.ML_SERVICE_URL}/adapter/import`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      return res.status(response.status).json(error);
    }

    const data = await response.json();
    res.json(data);
  })
);

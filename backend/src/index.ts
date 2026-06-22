import express from 'express';
import cors from 'cors';
import mongoose from 'mongoose';
import multer from 'multer';
import { env } from './config/env';
import { errorHandler } from './middleware/errorHandler';
import { adminRoutes } from './routes/admin/import';
import { adapterRoutes } from './routes/adapter';
import { profileRoutes } from './routes/profiles';
import { voiceRoutes } from './routes/voice';
import { qaRoutes } from './routes/qa';

const app = express();

app.use(cors({ origin: '*' }));
app.use(express.json());

// Multer for file uploads
const upload = multer({ storage: multer.memoryStorage() });

// Connect to MongoDB
mongoose.connect(env.MONGO_URI).catch(err => {
  console.error('MongoDB connection error:', err);
});

// Health check
app.get('/health', async (_req, res) => {
  try {
    // Check ML service health
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    let mlHealth = false;
    try {
      const mlResponse = await fetch(`${env.ML_SERVICE_URL}/health`, { signal: controller.signal });
      mlHealth = mlResponse.ok;
    } catch {
      mlHealth = false;
    } finally {
      clearTimeout(timeoutId);
    }

    // Check MongoDB
    const mongoHealth = mongoose.connection.readyState === 1;

    res.json({
      status: mongoHealth ? 'ok' : 'degraded',
      mongodb: mongoHealth,
      ml_service: mlHealth,
    });
  } catch (error) {
    res.status(503).json({
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

// Register API routes
app.use('/api/admin', adminRoutes);
app.use('/api/adapter', upload.single('file'), adapterRoutes);
app.use('/api/profiles', profileRoutes);
app.use('/api/voice', voiceRoutes);
app.use('/api/qa', qaRoutes);

app.use(errorHandler);

app.listen(env.PORT, () => {
  console.log(`Backend running on port ${env.PORT}`);
  console.log(`ML Service URL: ${env.ML_SERVICE_URL}`);
});

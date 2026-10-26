import { Router, Request, Response } from 'express';
import { checkDatabaseConnection } from '../../database';

export const healthRouter = Router();

/**
 * Liveness probe: returns 200 as long as the Node.js process is responsive.
 */
healthRouter.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({
    status: 'ok',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});

/**
 * Readiness probe: verifies that dependencies (PostgreSQL) are reachable.
 * Returns 200 if ready, or 503 if dependencies fail health check.
 */
healthRouter.get('/ready', async (_req: Request, res: Response) => {
  const dbHealth = await checkDatabaseConnection();

  if (dbHealth.connected) {
    res.status(200).json({
      status: 'ok',
      database: {
        status: 'connected',
        latencyMs: dbHealth.latencyMs,
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  res.status(503).json({
    status: 'degraded',
    database: {
      status: 'disconnected',
      error: dbHealth.error ?? 'Database ping failed',
    },
    timestamp: new Date().toISOString(),
  });
});

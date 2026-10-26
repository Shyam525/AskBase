import express, { Application, Request, Response, NextFunction } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { getConfig } from './config';
import { healthRouter } from './modules/health/health.routes';
import { errorHandler } from './middleware/error-handler';
import { NotFoundError } from './errors';

/**
 * Creates and configures the Express application instance.
 */
export function createApp(): Application {
  const config = getConfig();
  const app = express();

  // Security headers and CORS
  app.use(helmet());
  app.use(
    cors({
      origin: config.CORS_ORIGIN === '*' ? true : config.CORS_ORIGIN,
      credentials: true,
    })
  );

  // Body parser
  app.use(express.json({ limit: '1mb' }));

  // Root status check
  app.get('/', (_req: Request, res: Response) => {
    res.status(200).json({
      name: 'AskBase API',
      version: '0.1.0',
      status: 'operational',
    });
  });

  // Health and readiness routes
  app.use(healthRouter);
  app.use('/api', healthRouter);

  // 404 handler for undefined routes
  app.use((_req: Request, _res: Response, next: NextFunction) => {
    next(new NotFoundError('The requested endpoint was not found.'));
  });

  // Central error handling middleware
  app.use(errorHandler);

  return app;
}

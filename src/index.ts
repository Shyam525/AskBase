import { createApp } from './app';
import { getConfig } from './config';
import { getPool, closePool } from './database';
import { runMigrations } from './database/migrator';

async function bootstrap(): Promise<void> {
  const config = getConfig();

  // eslint-disable-next-line no-console
  console.log(`[AskBase] Starting backend server in "${config.NODE_ENV}" mode...`);

  // Auto-apply migrations in development
  if (config.NODE_ENV === 'development') {
    try {
      const pool = getPool();
      const migrationResult = await runMigrations(pool);
      if (migrationResult.applied.length > 0) {
        // eslint-disable-next-line no-console
        console.log(`[AskBase] Applied migrations: ${migrationResult.applied.join(', ')}`);
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn(
        `[AskBase] Note: Database migration did not run automatically on start: ${(err as Error).message}. Run 'npm run db:migrate' once PostgreSQL is available.`
      );
    }
  }

  const app = createApp();

  const server = app.listen(config.PORT, () => {
    // eslint-disable-next-line no-console
    console.log(`[AskBase] Server listening at http://localhost:${config.PORT}`);
    // eslint-disable-next-line no-console
    console.log(`[AskBase] Health: http://localhost:${config.PORT}/health`);
    // eslint-disable-next-line no-console
    console.log(`[AskBase] Ready:  http://localhost:${config.PORT}/ready`);
  });

  // Graceful shutdown
  const shutdown = async (signal: string) => {
    // eslint-disable-next-line no-console
    console.log(`[AskBase] Received ${signal}. Initiating graceful shutdown...`);

    server.close(async () => {
      // eslint-disable-next-line no-console
      console.log('[AskBase] HTTP server closed.');
      try {
        await closePool();
        // eslint-disable-next-line no-console
        console.log('[AskBase] Database pool closed.');
        process.exit(0);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('[AskBase] Error during database shutdown:', err);
        process.exit(1);
      }
    });

    // Force exit after 10 seconds if graceful shutdown hangs
    setTimeout(() => {
      // eslint-disable-next-line no-console
      console.error('[AskBase] Graceful shutdown timed out. Forcing exit.');
      process.exit(1);
    }, 10000).unref();
  };

  process.on('SIGTERM', () => void shutdown('SIGTERM'));
  process.on('SIGINT', () => void shutdown('SIGINT'));

  process.on('unhandledRejection', (reason) => {
    // eslint-disable-next-line no-console
    console.error('[AskBase] Unhandled promise rejection:', reason);
  });

  process.on('uncaughtException', (err) => {
    // eslint-disable-next-line no-console
    console.error('[AskBase] Uncaught exception:', err);
    process.exit(1);
  });
}

void bootstrap();

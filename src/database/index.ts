import { Pool, PoolClient, QueryResult, QueryResultRow } from 'pg';
import { getConfig } from '../config';

let pool: Pool | null = null;

/**
 * Initializes and returns the PostgreSQL connection pool.
 */
export function getPool(): Pool {
  if (!pool) {
    const config = getConfig();

    pool = new Pool({
      connectionString: config.DATABASE_URL,
      min: config.DATABASE_POOL_MIN,
      max: config.DATABASE_POOL_MAX,
      idleTimeoutMillis: config.DATABASE_IDLE_TIMEOUT_MS,
      connectionTimeoutMillis: config.DATABASE_CONNECTION_TIMEOUT_MS,
    });

    pool.on('error', (err) => {
      // eslint-disable-next-line no-console
      console.error('Unexpected error on idle PostgreSQL client:', err);
    });
  }

  return pool;
}

/**
 * Injects a custom pool instance (useful for testing with disposable/in-memory instances).
 */
export function setPool(customPool: Pool | null): void {
  pool = customPool;
}

/**
 * Gracefully shuts down the connection pool.
 */
export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}

/**
 * Convenience query helper that executes against the pool.
 */
export async function query<R extends QueryResultRow = QueryResultRow, I = unknown[]>(
  text: string,
  params?: I extends unknown[] ? I : unknown[]
): Promise<QueryResult<R>> {
  const p = getPool();
  return p.query<R>(text, params);
}

/**
 * Acquires a client from the pool for transactional workflows.
 */
export async function getClient(): Promise<PoolClient> {
  const p = getPool();
  return p.connect();
}

/**
 * Health check helper to verify database connectivity.
 */
export async function checkDatabaseConnection(): Promise<{
  connected: boolean;
  latencyMs: number;
  error?: string;
}> {
  const start = Date.now();
  try {
    const p = getPool();
    await p.query('SELECT 1');
    return {
      connected: true,
      latencyMs: Date.now() - start,
    };
  } catch (err) {
    return {
      connected: false,
      latencyMs: Date.now() - start,
      error: (err as Error).message,
    };
  }
}

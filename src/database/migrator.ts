import fs from 'fs';
import path from 'path';

export interface Queryable {
  query(text: string, params?: unknown[]): Promise<{ rows: Record<string, unknown>[] }>;
  exec?(sql: string): Promise<unknown>;
}

export interface MigrationResult {
  applied: string[];
  skipped: string[];
}

/**
 * Migration runner that executes SQL migration files in transactional order.
 * Tracks applied migrations in a schema_migrations table.
 */
export async function runMigrations(
  client: Queryable,
  migrationsDir?: string
): Promise<MigrationResult> {
  let dir = migrationsDir;

  if (!dir) {
    const candidateDirs = [
      path.join(__dirname, 'migrations'),
      path.join(process.cwd(), 'dist', 'database', 'migrations'),
      path.join(process.cwd(), 'src', 'database', 'migrations'),
    ];

    dir = candidateDirs.find((candidate) => fs.existsSync(candidate));
    if (!dir) {
      throw new Error(`Migrations directory not found in candidate paths: ${candidateDirs.join(', ')}`);
    }
  }

  // Ensure migrations tracking table exists
  await client.query(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL UNIQUE,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `);

  // Query already applied migrations
  const { rows } = await client.query('SELECT name FROM schema_migrations ORDER BY id ASC');
  const appliedSet = new Set<string>(rows.map((r) => r.name as string));

  if (!fs.existsSync(dir)) {
    throw new Error(`Migrations directory does not exist: ${dir}`);
  }

  const files = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.sql'))
    .sort();

  const applied: string[] = [];
  const skipped: string[] = [];

  for (const file of files) {
    if (appliedSet.has(file)) {
      skipped.push(file);
      continue;
    }

    const filePath = path.join(dir, file);
    const sql = fs.readFileSync(filePath, 'utf-8');

    // Run migration inside transaction
    await client.query('BEGIN');
    try {
      if (typeof client.exec === 'function') {
        await client.exec(sql);
      } else {
        await client.query(sql);
      }
      await client.query(
        'INSERT INTO schema_migrations (name, applied_at) VALUES ($1, NOW())',
        [file]
      );
      await client.query('COMMIT');
      applied.push(file);
    } catch (err) {
      await client.query('ROLLBACK');
      throw new Error(`Failed to apply migration "${file}": ${(err as Error).message}`);
    }
  }

  return { applied, skipped };
}

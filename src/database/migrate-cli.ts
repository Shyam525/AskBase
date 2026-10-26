import { getPool, closePool } from './index';
import { runMigrations } from './migrator';

async function main(): Promise<void> {
  // eslint-disable-next-line no-console
  console.log('Starting AskBase database migration runner...');

  try {
    const pool = getPool();
    const result = await runMigrations(pool);

    // eslint-disable-next-line no-console
    console.log(`Migrations complete.`);
    // eslint-disable-next-line no-console
    console.log(`- Applied (${result.applied.length}): ${result.applied.join(', ') || 'None'}`);
    // eslint-disable-next-line no-console
    console.log(`- Skipped (${result.skipped.length}): ${result.skipped.join(', ') || 'None'}`);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('Migration failed:', err);
    process.exitCode = 1;
  } finally {
    await closePool();
  }
}

if (require.main === module) {
  void main();
}

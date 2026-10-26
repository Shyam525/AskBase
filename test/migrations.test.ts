import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import path from 'path';
import { PGlite } from '@electric-sql/pglite';
import { runMigrations, Queryable } from '../src/database/migrator';

describe('Database Migrations and Schema Constraints (Real Disposable PostgreSQL)', () => {
  let pglite: PGlite;
  let client: Queryable;
  const migrationsDir = path.join(__dirname, '../src/database/migrations');

  beforeEach(async () => {
    pglite = new PGlite();
    client = {
      query: async (text: string, params?: unknown[]) => {
        const res = await pglite.query(text, params as unknown[] | undefined);
        return { rows: res.rows as Record<string, unknown>[] };
      },
      exec: async (sql: string) => {
        await pglite.exec(sql);
      },
    };
  });

  afterEach(async () => {
    await pglite.close();
  });

  it('applies initial migration successfully and creates schema_migrations tracking table', async () => {
    const result = await runMigrations(client, migrationsDir);

    expect(result.applied).toContain('001_initial_schema.sql');
    expect(result.skipped).toHaveLength(0);

    // Verify tracking table recorded the migration
    const { rows } = await client.query('SELECT name FROM schema_migrations');
    expect(rows.map((r) => r.name)).toContain('001_initial_schema.sql');
  });

  it('is idempotent when run multiple times without re-executing migrations', async () => {
    // First run
    const first = await runMigrations(client, migrationsDir);
    expect(first.applied).toHaveLength(1);

    // Second run
    const second = await runMigrations(client, migrationsDir);
    expect(second.applied).toHaveLength(0);
    expect(second.skipped).toContain('001_initial_schema.sql');
  });

  it('enforces users table constraints (UUID PK, case-insensitive email uniqueness)', async () => {
    await runMigrations(client, migrationsDir);

    // Insert initial user
    const insertRes = await client.query(
      `INSERT INTO users (email, password_hash, name)
       VALUES ($1, $2, $3)
       RETURNING id, email, created_at`,
      ['engineer@askbase.dev', 'dummy-hash-123', 'Senior Engineer']
    );

    expect(insertRes.rows).toHaveLength(1);
    const userId = insertRes.rows[0].id as string;
    expect(userId).toBeDefined();
    // Validate UUID format
    expect(userId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);

    // Attempt inserting duplicate email with different casing
    await expect(
      client.query(
        `INSERT INTO users (email, password_hash, name)
         VALUES ($1, $2, $3)`,
        ['ENGINEER@askbase.dev', 'dummy-hash-456', 'Duplicate Engineer']
      )
    ).rejects.toThrow();
  });

  it('enforces workspaces table constraints (slug uniqueness case-insensitively)', async () => {
    await runMigrations(client, migrationsDir);

    const insertRes = await client.query(
      `INSERT INTO workspaces (name, slug)
       VALUES ($1, $2)
       RETURNING id, slug`,
      ['Acme Corp', 'acme-corp']
    );

    expect(insertRes.rows).toHaveLength(1);
    const wsId = insertRes.rows[0].id as string;
    expect(wsId).toBeDefined();

    // Attempt inserting duplicate slug with different casing
    await expect(
      client.query(
        `INSERT INTO workspaces (name, slug)
         VALUES ($1, $2)`,
        ['Another Acme', 'ACME-CORP']
      )
    ).rejects.toThrow();
  });

  it('enforces workspace memberships foreign keys, uniqueness, and cascading deletes', async () => {
    await runMigrations(client, migrationsDir);

    // Create user and workspace
    const userRes = await client.query(
      `INSERT INTO users (email, password_hash, name)
       VALUES ('owner@askbase.dev', 'hash', 'Owner')
       RETURNING id`
    );
    const userId = userRes.rows[0].id as string;

    const wsRes = await client.query(
      `INSERT INTO workspaces (name, slug)
       VALUES ('Base Workspace', 'base-workspace')
       RETURNING id`
    );
    const wsId = wsRes.rows[0].id as string;

    // Create membership
    const memberRes = await client.query(
      `INSERT INTO workspace_memberships (workspace_id, user_id, role)
       VALUES ($1, $2, $3)
       RETURNING id, role`,
      [wsId, userId, 'owner']
    );
    expect(memberRes.rows[0].role).toBe('owner');

    // Duplicate membership for same user in same workspace must fail
    await expect(
      client.query(
        `INSERT INTO workspace_memberships (workspace_id, user_id, role)
         VALUES ($1, $2, $3)`,
        [wsId, userId, 'member']
      )
    ).rejects.toThrow();

    // Foreign key violation when workspace does not exist
    const nonExistentUuid = '00000000-0000-0000-0000-000000000000';
    await expect(
      client.query(
        `INSERT INTO workspace_memberships (workspace_id, user_id, role)
         VALUES ($1, $2, $3)`,
        [nonExistentUuid, userId, 'member']
      )
    ).rejects.toThrow();

    // Verify CASCADE: deleting workspace automatically removes membership
    await client.query('DELETE FROM workspaces WHERE id = $1', [wsId]);
    const remainingMembers = await client.query(
      'SELECT id FROM workspace_memberships WHERE workspace_id = $1',
      [wsId]
    );
    expect(remainingMembers.rows).toHaveLength(0);
  });
});

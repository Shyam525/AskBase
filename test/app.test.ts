import { describe, it, expect, vi, beforeEach } from 'vitest';
import request from 'supertest';
import { createApp } from '../src/app';
import * as databaseModule from '../src/database';

describe('Express Application & Core Endpoints', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('GET / returns operational metadata', async () => {
    const app = createApp();
    const res = await request(app).get('/');

    expect(res.status).toBe(200);
    expect(res.body.name).toBe('AskBase API');
    expect(res.body.status).toBe('operational');
  });

  it('GET /health returns liveness status', async () => {
    const app = createApp();
    const res = await request(app).get('/health');

    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(typeof res.body.uptime).toBe('number');
    expect(res.body.timestamp).toBeDefined();
  });

  it('GET /ready returns 200 when database connection is healthy', async () => {
    vi.spyOn(databaseModule, 'checkDatabaseConnection').mockResolvedValueOnce({
      connected: true,
      latencyMs: 3,
    });

    const app = createApp();
    const res = await request(app).get('/ready');

    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(res.body.database.status).toBe('connected');
    expect(res.body.database.latencyMs).toBe(3);
  });

  it('GET /ready returns 503 when database is degraded or unreachable', async () => {
    vi.spyOn(databaseModule, 'checkDatabaseConnection').mockResolvedValueOnce({
      connected: false,
      latencyMs: 15,
      error: 'Connection timeout',
    });

    const app = createApp();
    const res = await request(app).get('/ready');

    expect(res.status).toBe(503);
    expect(res.body.status).toBe('degraded');
    expect(res.body.database.status).toBe('disconnected');
    expect(res.body.database.error).toBe('Connection timeout');
  });

  it('returns 404 with standardized error JSON for unknown routes', async () => {
    const app = createApp();
    const res = await request(app).get('/api/unknown-route-12345');

    expect(res.status).toBe(404);
    expect(res.body.error).toBeDefined();
    expect(res.body.error.code).toBe('NOT_FOUND');
    expect(res.body.error.message).toContain('not found');
  });

  it('returns 400 MALFORMED_JSON for malformed JSON request bodies', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/ready')
      .set('Content-Type', 'application/json')
      .send('{"invalid json: missing closing brace');

    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('MALFORMED_JSON');
  });
});

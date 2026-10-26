import { describe, it, expect } from 'vitest';
import express, { Request, Response } from 'express';
import request from 'supertest';
import { z } from 'zod';
import { validate } from '../src/middleware/validate';
import { errorHandler } from '../src/middleware/error-handler';

describe('Validation Middleware', () => {
  const app = express();
  app.use(express.json());

  const testSchema = {
    body: z.object({
      name: z.string().min(2),
      email: z.string().email(),
      age: z.number().int().positive().optional(),
    }),
    query: z.object({
      includeInactive: z.enum(['true', 'false']).optional(),
    }),
    params: z.object({
      id: z.string().uuid(),
    }),
  };

  app.post(
    '/items/:id',
    validate(testSchema),
    (req: Request, res: Response) => {
      res.status(200).json({
        params: req.params,
        query: req.query,
        body: req.body,
      });
    }
  );

  app.use(errorHandler);

  it('accepts valid params, query, and body', async () => {
    const validUuid = '123e4567-e89b-12d3-a456-426614174000';
    const res = await request(app)
      .post(`/items/${validUuid}?includeInactive=true`)
      .send({
        name: 'AskBase',
        email: 'user@example.com',
        age: 25,
      });

    expect(res.status).toBe(200);
    expect(res.body.body.name).toBe('AskBase');
    expect(res.body.params.id).toBe(validUuid);
    expect(res.body.query.includeInactive).toBe('true');
  });

  it('rejects invalid email and name in body with structured 400 error', async () => {
    const validUuid = '123e4567-e89b-12d3-a456-426614174000';
    const res = await request(app)
      .post(`/items/${validUuid}`)
      .send({
        name: 'A',
        email: 'not-an-email',
      });

    expect(res.status).toBe(400);
    expect(res.body.error).toBeDefined();
    expect(res.body.error.code).toBe('VALIDATION_ERROR');
    expect(res.body.error.message).toBe('Request validation failed');
    expect(Array.isArray(res.body.error.details)).toBe(true);
    expect(res.body.error.details.length).toBe(2);

    const fields = res.body.error.details.map((d: { field: string }) => d.field);
    expect(fields).toContain('body.name');
    expect(fields).toContain('body.email');
  });

  it('rejects invalid path param format with structured 400 error', async () => {
    const res = await request(app)
      .post('/items/not-a-uuid')
      .send({
        name: 'Valid Name',
        email: 'test@example.com',
      });

    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('VALIDATION_ERROR');
    const fields = res.body.error.details.map((d: { field: string }) => d.field);
    expect(fields).toContain('params.id');
  });
});

import { describe, it, expect } from 'vitest';
import {
  AppError,
  ValidationError,
  NotFoundError,
  ConflictError,
  UnauthorizedError,
  ForbiddenError,
  BadRequestError,
  ServiceUnavailableError,
} from '../src/errors';

describe('Error Hierarchy', () => {
  it('instantiates base AppError with defaults and operational flag', () => {
    const error = new AppError('Something went wrong');
    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(AppError);
    expect(error.message).toBe('Something went wrong');
    expect(error.statusCode).toBe(500);
    expect(error.code).toBe('INTERNAL_ERROR');
    expect(error.isOperational).toBe(true);
  });

  it('correctly maps status codes and codes for subclasses', () => {
    const validation = new ValidationError('Bad input', [{ field: 'email', message: 'Invalid' }]);
    expect(validation.statusCode).toBe(400);
    expect(validation.code).toBe('VALIDATION_ERROR');
    expect(validation.details).toEqual([{ field: 'email', message: 'Invalid' }]);

    const badReq = new BadRequestError('Bad syntax');
    expect(badReq.statusCode).toBe(400);
    expect(badReq.code).toBe('BAD_REQUEST');

    const unauthorized = new UnauthorizedError();
    expect(unauthorized.statusCode).toBe(401);
    expect(unauthorized.code).toBe('UNAUTHORIZED');

    const forbidden = new ForbiddenError();
    expect(forbidden.statusCode).toBe(403);
    expect(forbidden.code).toBe('FORBIDDEN');

    const notFound = new NotFoundError('Workspace not found');
    expect(notFound.statusCode).toBe(404);
    expect(notFound.code).toBe('NOT_FOUND');

    const conflict = new ConflictError('Slug already exists');
    expect(conflict.statusCode).toBe(409);
    expect(conflict.code).toBe('CONFLICT');

    const unavailable = new ServiceUnavailableError('DB down');
    expect(unavailable.statusCode).toBe(503);
    expect(unavailable.code).toBe('SERVICE_UNAVAILABLE');
  });
});

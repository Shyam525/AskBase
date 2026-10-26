import { Request, Response, NextFunction } from 'express';
import { AppError } from '../errors';

interface DatabaseErrorLike extends Error {
  code?: string;
  detail?: string;
  constraint?: string;
}

/**
 * Central Express error-handling middleware.
 * Guarantees consistent error JSON contracts and prevents leakage of
 * internal exceptions, stack traces, or database details to API clients.
 */
export function errorHandler(
  err: Error | AppError | DatabaseErrorLike,
  _req: Request,
  res: Response,
  _next: NextFunction
): void {
  // 1. Handled operational application errors
  if (err instanceof AppError) {
    res.status(err.statusCode).json({
      error: {
        code: err.code,
        message: err.message,
        ...(err.details !== undefined ? { details: err.details } : {}),
      },
    });
    return;
  }

  // 2. Malformed JSON body from express.json()
  if (err instanceof SyntaxError && 'status' in err && (err as { status: unknown }).status === 400) {
    res.status(400).json({
      error: {
        code: 'MALFORMED_JSON',
        message: 'Invalid JSON payload received in request body.',
      },
    });
    return;
  }

  // 3. PostgreSQL driver error mapping
  const dbErr = err as DatabaseErrorLike;
  if (dbErr.code) {
    switch (dbErr.code) {
      case '23505': // unique_violation
        res.status(409).json({
          error: {
            code: 'RESOURCE_CONFLICT',
            message: 'A record with this identifier or unique attribute already exists.',
          },
        });
        return;
      case '23503': // foreign_key_violation
        res.status(400).json({
          error: {
            code: 'FOREIGN_KEY_VIOLATION',
            message: 'Referenced entity does not exist or relation is constrained.',
          },
        });
        return;
      case '22P02': // invalid_text_representation (e.g. invalid UUID format)
        res.status(400).json({
          error: {
            code: 'INVALID_INPUT_SYNTAX',
            message: 'One or more input values are not formatted correctly.',
          },
        });
        return;
      default:
        break;
    }
  }

  // 4. Unhandled / programmer errors: log securely and sanitize output
  if (process.env.NODE_ENV !== 'test') {
    // eslint-disable-next-line no-console
    console.error('Unhandled internal error:', {
      name: err.name,
      message: err.message,
      stack: err.stack,
    });
  }

  res.status(500).json({
    error: {
      code: 'INTERNAL_SERVER_ERROR',
      message: 'An unexpected internal error occurred.',
    },
  });
}

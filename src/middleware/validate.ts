import { Request, Response, NextFunction } from 'express';
import { AnyZodObject, ZodError } from 'zod';
import { ValidationError, ErrorDetail } from '../errors';

export interface RequestValidationSchema {
  body?: AnyZodObject;
  query?: AnyZodObject;
  params?: AnyZodObject;
}

/**
 * Express middleware factory for validating request body, query, and path parameters.
 * Validates against Zod schemas and passes a structured ValidationError to next() on failure.
 */
export function validate(schema: RequestValidationSchema) {
  return async (req: Request, _res: Response, next: NextFunction): Promise<void> => {
    const errorDetails: ErrorDetail[] = [];

    try {
      if (schema.params) {
        req.params = await schema.params.parseAsync(req.params);
      }
    } catch (err) {
      if (err instanceof ZodError) {
        formatZodIssues(err, 'params', errorDetails);
      } else {
        return next(err);
      }
    }

    try {
      if (schema.query) {
        req.query = await schema.query.parseAsync(req.query);
      }
    } catch (err) {
      if (err instanceof ZodError) {
        formatZodIssues(err, 'query', errorDetails);
      } else {
        return next(err);
      }
    }

    try {
      if (schema.body) {
        req.body = await schema.body.parseAsync(req.body);
      }
    } catch (err) {
      if (err instanceof ZodError) {
        formatZodIssues(err, 'body', errorDetails);
      } else {
        return next(err);
      }
    }

    if (errorDetails.length > 0) {
      return next(new ValidationError('Request validation failed', errorDetails));
    }

    next();
  };
}

function formatZodIssues(
  error: ZodError,
  source: 'body' | 'query' | 'params',
  target: ErrorDetail[]
): void {
  for (const issue of error.issues) {
    const fieldPath = issue.path.length > 0 ? issue.path.join('.') : source;
    target.push({
      field: `${source}.${fieldPath}`,
      message: issue.message,
      code: issue.code,
    });
  }
}

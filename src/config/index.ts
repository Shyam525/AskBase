import dotenv from 'dotenv';
import { z } from 'zod';

// Load .env file into process.env before parsing
dotenv.config();

export const envSchema = z
  .object({
    NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
    PORT: z.coerce.number().int().min(1).max(65535).default(5000),

    // Database configuration
    DATABASE_URL: z
      .string()
      .min(1, 'DATABASE_URL is required')
      .default('postgresql://postgres:secret@localhost:5432/askbase'),
    DATABASE_POOL_MIN: z.coerce.number().int().nonnegative().default(2),
    DATABASE_POOL_MAX: z.coerce.number().int().positive().default(10),
    DATABASE_CONNECTION_TIMEOUT_MS: z.coerce.number().int().positive().default(5000),
    DATABASE_IDLE_TIMEOUT_MS: z.coerce.number().int().positive().default(30000),

    // Authentication & cryptography configuration
    JWT_SECRET: z.string().min(16).default('local-development-secret-change-me-in-production-min-32-chars'),
    JWT_EXPIRES_IN: z.string().default('15m'),
    JWT_ISSUER: z.string().default('askbase-api'),
    JWT_AUDIENCE: z.string().default('askbase-clients'),
    BCRYPT_SALT_ROUNDS: z.coerce.number().int().min(8).max(14).default(10),

    // HTTP / Network settings
    CORS_ORIGIN: z.string().default('*'),
    LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  })
  .refine(
    (data) => {
      // In production, enforce stronger secret length
      if (data.NODE_ENV === 'production' && data.JWT_SECRET.length < 32) {
        return false;
      }
      return true;
    },
    {
      message: 'JWT_SECRET must be at least 32 characters in production',
      path: ['JWT_SECRET'],
    }
  );

export type Config = z.infer<typeof envSchema>;

let cachedConfig: Config | null = null;

export class ConfigurationError extends Error {
  public readonly issues: z.ZodIssue[];

  constructor(issues: z.ZodIssue[]) {
    const formatted = issues
      .map((issue) => `  - ${issue.path.join('.')}: ${issue.message}`)
      .join('\n');
    super(`Invalid environment configuration:\n${formatted}`);
    this.name = 'ConfigurationError';
    this.issues = issues;
  }
}

/**
 * Loads, validates, and freezes the application configuration.
 * Throws a descriptive ConfigurationError if validation fails.
 */
export function loadConfig(envOverride?: Record<string, unknown>): Config {
  const envToValidate = envOverride ?? process.env;
  const result = envSchema.safeParse(envToValidate);

  if (!result.success) {
    throw new ConfigurationError(result.error.issues);
  }

  return Object.freeze(result.data);
}

/**
 * Returns the cached configuration instance, loading it on first call.
 */
export function getConfig(): Config {
  if (!cachedConfig) {
    cachedConfig = loadConfig();
  }
  return cachedConfig;
}

/**
 * Resets the cached configuration (primarily used in tests).
 */
export function resetConfig(): void {
  cachedConfig = null;
}

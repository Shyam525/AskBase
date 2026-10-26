import bcrypt from 'bcryptjs';
import jwt, { SignOptions } from 'jsonwebtoken';
import { getConfig } from '../../config';

/**
 * Production-ready cryptographic utilities for password hashing and JWT issuance.
 *
 * Requirements:
 * - Passwords are hashed using bcrypt with configurable salt rounds (default 10).
 * - Tokens are signed using HMAC-SHA256 with JWT_SECRET (must be >=32 chars in production).
 * - Configuration parameters are sourced from validated application config.
 */

/**
 * Hashes a plaintext password using bcrypt.
 */
export async function hashPassword(password: string, rounds?: number): Promise<string> {
  const config = getConfig();
  const saltRounds = rounds ?? config.BCRYPT_SALT_ROUNDS;
  return bcrypt.hash(password, saltRounds);
}

/**
 * Verifies a plaintext password against a stored bcrypt hash.
 */
export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

/**
 * Signs a JWT payload with application credentials.
 */
export function signJwt(
  payload: Record<string, unknown>,
  options?: SignOptions
): string {
  const config = getConfig();
  const signOptions: SignOptions = {
    issuer: config.JWT_ISSUER,
    audience: config.JWT_AUDIENCE,
    expiresIn: config.JWT_EXPIRES_IN as SignOptions['expiresIn'],
    ...options,
  };

  return jwt.sign(payload, config.JWT_SECRET, signOptions);
}

/**
 * Verifies and decodes a JWT token.
 */
export function verifyJwt<T = Record<string, unknown>>(
  token: string,
  options?: jwt.VerifyOptions
): T {
  const config = getConfig();
  return jwt.verify(token, config.JWT_SECRET, {
    issuer: config.JWT_ISSUER,
    audience: config.JWT_AUDIENCE,
    ...options,
  }) as T;
}

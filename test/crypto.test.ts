import { describe, it, expect } from 'vitest';
import { hashPassword, verifyPassword, signJwt, verifyJwt } from '../src/modules/auth/crypto';

describe('Cryptographic Utilities', () => {
  it('hashes and successfully verifies a password with bcrypt', async () => {
    const raw = 'SuperSecret123!';
    const hashed = await hashPassword(raw, 10);

    expect(hashed).toBeDefined();
    expect(hashed).not.toBe(raw);
    expect(hashed.startsWith('$2')).toBe(true);

    const isMatch = await verifyPassword(raw, hashed);
    expect(isMatch).toBe(true);

    const isMismatch = await verifyPassword('WrongPassword', hashed);
    expect(isMismatch).toBe(false);
  });

  it('signs and verifies a valid JWT payload', () => {
    const payload = {
      userId: '123e4567-e89b-12d3-a456-426614174000',
      email: 'engineer@askbase.dev',
      role: 'admin',
    };

    const token = signJwt(payload);
    expect(typeof token).toBe('string');
    expect(token.split('.').length).toBe(3);

    const decoded = verifyJwt<{ userId: string; email: string; role: string; iss: string }>(token);
    expect(decoded.userId).toBe(payload.userId);
    expect(decoded.email).toBe(payload.email);
    expect(decoded.role).toBe(payload.role);
    expect(decoded.iss).toBe('askbase-api');
  });

  it('rejects tampered or forged tokens', () => {
    const token = signJwt({ userId: 'alice' });
    const tampered = token.slice(0, -5) + 'abcde';

    expect(() => verifyJwt(tampered)).toThrow();
  });
});

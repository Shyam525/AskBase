import { describe, it, expect, beforeEach } from 'vitest';
import { loadConfig, resetConfig, ConfigurationError } from '../src/config';

describe('Configuration Schema', () => {
  beforeEach(() => {
    resetConfig();
  });

  it('loads valid default configuration', () => {
    const config = loadConfig({
      NODE_ENV: 'test',
      PORT: '5000',
      DATABASE_URL: 'postgresql://postgres:secret@localhost:5432/askbase_test',
      JWT_SECRET: 'super-secret-key-for-testing-purposes-123',
    });

    expect(config.NODE_ENV).toBe('test');
    expect(config.PORT).toBe(5000);
    expect(config.DATABASE_URL).toBe('postgresql://postgres:secret@localhost:5432/askbase_test');
    expect(config.BCRYPT_SALT_ROUNDS).toBe(10);
    expect(config.LOG_LEVEL).toBe('info');
    expect(Object.isFrozen(config)).toBe(true);
  });

  it('rejects invalid port numbers', () => {
    expect(() =>
      loadConfig({
        PORT: '99999',
      })
    ).toThrow(ConfigurationError);

    expect(() =>
      loadConfig({
        PORT: '-1',
      })
    ).toThrow(ConfigurationError);
  });

  it('rejects invalid NODE_ENV', () => {
    expect(() =>
      loadConfig({
        NODE_ENV: 'staging',
      })
    ).toThrow(ConfigurationError);
  });

  it('enforces >=32 character JWT_SECRET in production mode', () => {
    expect(() =>
      loadConfig({
        NODE_ENV: 'production',
        JWT_SECRET: 'short-secret',
      })
    ).toThrow(ConfigurationError);

    const validProduction = loadConfig({
      NODE_ENV: 'production',
      JWT_SECRET: 'this-is-a-valid-production-secret-with-more-than-32-characters',
    });
    expect(validProduction.NODE_ENV).toBe('production');
  });

  it('formats validation issues clearly in ConfigurationError message', () => {
    try {
      loadConfig({
        PORT: 'invalid-port',
      });
      expect.fail('Should have thrown ConfigurationError');
    } catch (err) {
      expect(err).toBeInstanceOf(ConfigurationError);
      expect((err as ConfigurationError).message).toContain('PORT');
    }
  });
});

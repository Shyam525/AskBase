export interface User {
  id: string;
  email: string;
  password_hash: string;
  name: string;
  created_at: Date;
  updated_at: Date;
}

export interface CreateUserInput {
  email: string;
  password_hash: string;
  name: string;
}

export type SafeUser = Omit<User, 'password_hash'>;

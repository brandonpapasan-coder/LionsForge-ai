export type AuthCredentials = {
  email: string;
  secret: string;
  full_name?: string;
};

export type AuthToken = {
  access_token: string;
  token_type: string;
};

export type AuthUser = {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
};

export type AuthResult = {
  ok: boolean;
  message: string;
  user?: AuthUser;
};

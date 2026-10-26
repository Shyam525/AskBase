export type WorkspaceRole = 'owner' | 'admin' | 'member';

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  created_at: Date;
  updated_at: Date;
}

export interface WorkspaceMembership {
  id: string;
  workspace_id: string;
  user_id: string;
  role: WorkspaceRole;
  created_at: Date;
  updated_at: Date;
}

export interface CreateWorkspaceInput {
  name: string;
  slug: string;
}

export interface AddMemberInput {
  workspace_id: string;
  user_id: string;
  role?: WorkspaceRole;
}

# ADR 0001: Document Identity vs. Binary Equality and Duplicate Handling Policy

## Status
Pending Policy Determination (Status Quo: Non-destructive Content-Hash Identification)

## Context
In AskBase, users upload organizational knowledge in multiple file formats (text, Markdown, PDF). A critical requirement is preserving document provenance, version history, and retrievable evidence.

When users upload files, two distinct concepts must not be conflated:
1. **Binary Equality**: Two uploaded files have the exact same SHA-256 cryptographic digest of their binary contents.
2. **Document Identity**: Two records represent the same logical entity within an organization's knowledge hierarchy (e.g., "Engineering Handbook", "Q3 Financial Report", "Employee Onboarding Checklist").

Identical bytes can occur under multiple valid organizational scenarios:
- **Renaming / Relabeling**: A document template is copied and uploaded under different logical titles in different workspaces or folders.
- **Cross-Workspace Sharing**: Different teams upload the same vendor contract, policy PDF, or reference manual into their respective workspaces.
- **Independent Coincidence**: Two separate users independently upload identical files without intending to merge their logical tracking, permissions, or lifecycle.
- **Intentional Re-upload**: A user re-uploads an unmodified file to a document to test or verify the ingestion pipeline.

Conversely, files with different binary hashes often represent the *exact same* logical document across time (e.g., version 1 vs version 2 with a typo fix).

Automatically merging, re-pointing, or deduplicating records simply because their SHA-256 hashes match introduces major risks:
- **Permission Leaks**: If Workspace A has confidential access to Document X, and Workspace B uploads an identical public document that gets merged into X, access controls and tenant isolation are compromised.
- **Broken Provenance & Citation Invalidation**: If an existing citation points to Version 1 of Document A, silently collapsing it with Document B breaks auditing and reviewability.
- **Accidental Deletion**: If a user deletes Document B, and Document B was deduplicated to share backing storage with Document A, naive cascade deletion could destroy Document A or corrupt historical answers.

## Decision Options Considered

### Option 1: Automatic Deduplication & Content-Addressable Storage (CAS)
- **Mechanism**: Use content SHA-256 as the primary storage key. If a matching hash exists anywhere in the system, skip storage and create a pointer to the existing storage record.
- **Pros**: Saves disk storage; eliminates redundant chunking and embedding computation.
- **Cons**: High complexity in cross-tenant isolation and reference counting. High risk of accidental data leaks or cascade deletion bugs across workspace boundaries.

### Option 2: Automatic Version Deduplication Within Logical Document Only
- **Mechanism**: If a user uploads a new version of Document A whose hash matches an existing version of Document A, reject the upload or return the existing version without incrementing the version counter.
- **Pros**: Prevents redundant version growth within a single document.
- **Cons**: May confuse automated sync pipelines or users expecting sequential revision tracking (e.g., "I re-ran the export and uploaded version 3").

### Option 3: Automatic Document Merging by Hash
- **Mechanism**: If an uploaded file matches the hash of an existing document in the same workspace, automatically discard the new document record and link to the existing document.
- **Pros**: Keeps document lists clean of duplicates.
- **Cons**: Silently overrides user intent if the user deliberately wanted two separate document entries (e.g., templates or categorized items).

### Option 4: Explicit Identification with Pending Policy (Selected Baseline)
- **Mechanism**:
  1. Compute and persist the SHA-256 content hash for every uploaded binary at ingestion time.
  2. Maintain strict separation between `Document` (logical entity) and `DocumentVersion` (immutable snapshot).
  3. Index `content_hash` at the database level and expose exact content-hash match indicators via the API (`duplicate_of_version_id`, `matching_versions_in_workspace`).
  4. **Do not** automatically merge, delete, or re-route documents based on hash matching.
  5. Leave the active deduplication/merge policy explicitly pending future user-driven review or workspace-level configuration.

## Consequences

### Positive
- **Guaranteed Provenance**: Every answer citation links to an unambiguous `document_id` and `version_id`. Historical versions are immutable.
- **Tenant & Workspace Safety**: No risk of cross-workspace data bleed or accidental cross-tenant dependencies.
- **Transparency**: Reviewers and administrators can detect duplicate content via API metadata without suffering unintended destructive side effects.
- **Reversibility**: Leaves all architectural options open for future configurable merge strategies without needing data migration.

### Negative / Trade-offs
- Multiple identical files uploaded intentionally or accidentally will consume proportional disk space and generate redundant chunks/embeddings.
- Search queries may return passages from two identical documents if both are active in the same workspace (mitigated by score ranking and distinct document citations).

## Pending Action Items
- Monitor real-world workspace storage utilization and duplicate upload frequency.
- Evaluate tenant-level configuration options: e.g., `allow_duplicate_hashes: true/false` or prompt on UI: "A document with identical content already exists: [Document Title]. Do you wish to create a reference or continue as a new document?".

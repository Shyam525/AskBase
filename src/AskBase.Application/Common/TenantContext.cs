namespace AskBase.Application.Common;

/// <summary>
/// Scoped service — one fresh instance per HTTP request.
///
/// Flow:
///   1. JWT is validated by AddAuthentication middleware
///   2. TenantMiddleware reads "tenant_id" claim -> sets TenantContext.TenantId
///   3. AppDbContext reads TenantContext.TenantId in HasQueryFilter(...)
///   4. Every EF query automatically adds: WHERE org_id = @TenantId
/// </summary>
public class TenantContext
{
    public Guid TenantId { get; set; } = Guid.Empty;
    public bool HasTenant => TenantId != Guid.Empty;
}

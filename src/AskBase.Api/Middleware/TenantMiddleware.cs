using AskBase.Application.Common;

namespace AskBase.Api.Middleware;

public class TenantMiddleware
{
    private readonly RequestDelegate _next;

    public TenantMiddleware(RequestDelegate next) => _next = next;

    public async Task InvokeAsync(HttpContext context, TenantContext tenantContext)
    {
        var claim = context.User?.FindFirst("tenant_id");

        if (claim != null && Guid.TryParse(claim.Value, out var tenantId))
        {
            tenantContext.TenantId = tenantId;
        }

        await _next(context);
    }
}

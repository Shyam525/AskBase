using AskBase.Application.Common;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace AskBase.Infrastructure.Data;

/// <summary>
/// Used ONLY by EF Core command-line tools (dotnet ef migrations add).
/// Without this, running migrations fails because tools cannot resolve
/// TenantContext from DI at design time.
/// </summary>
public class AppDbContextFactory : IDesignTimeDbContextFactory<AppDbContext>
{
    public AppDbContext CreateDbContext(string[] args)
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseNpgsql("Host=localhost;Database=askbase;Username=postgres;Password=secret")
            .Options;

        return new AppDbContext(options, new TenantContext());
    }
}

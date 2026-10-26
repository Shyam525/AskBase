using AskBase.Application.Common;
using AskBase.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace AskBase.Infrastructure.Data;

public class AppDbContext : DbContext
{
    private readonly TenantContext _tenant;

    public AppDbContext(DbContextOptions<AppDbContext> options, TenantContext tenant)
        : base(options)
    {
        _tenant = tenant;
    }

    public DbSet<Organization> Organizations => Set<Organization>();
    public DbSet<User> Users => Set<User>();
    public DbSet<RefreshToken> RefreshTokens => Set<RefreshToken>();

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);

        builder.Entity<Organization>(e =>
        {
            e.ToTable("organizations");
            e.Property(o => o.Id).HasColumnName("id");
            e.Property(o => o.Name).HasColumnName("name").IsRequired();
            e.Property(o => o.Slug).HasColumnName("slug").IsRequired();
            e.Property(o => o.Plan).HasColumnName("plan").HasDefaultValue("free");
            e.Property(o => o.StripeCustomerId).HasColumnName("stripe_customer_id");
            e.Property(o => o.StripeSubscriptionId).HasColumnName("stripe_subscription_id");
            e.Property(o => o.SeatsLimit).HasColumnName("seats_limit").HasDefaultValue(25);
            e.Property(o => o.SourcesLimit).HasColumnName("sources_limit").HasDefaultValue(3);
            e.Property(o => o.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("NOW()");
            e.HasIndex(o => o.Slug).IsUnique();
        });

        builder.Entity<User>(e =>
        {
            e.ToTable("users");
            e.Property(u => u.Id).HasColumnName("id");
            e.Property(u => u.OrgId).HasColumnName("org_id");
            e.Property(u => u.Email).HasColumnName("email").IsRequired();
            e.Property(u => u.PasswordHash).HasColumnName("password_hash").IsRequired();
            e.Property(u => u.Role).HasColumnName("role").HasDefaultValue("member");
            e.Property(u => u.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("NOW()");
            e.HasIndex(u => new { u.OrgId, u.Email }).IsUnique();

            e.HasOne(u => u.Organization)
                .WithMany(o => o.Users)
                .HasForeignKey(u => u.OrgId)
                .OnDelete(DeleteBehavior.Cascade);

            e.HasQueryFilter(u => u.OrgId == _tenant.TenantId);
        });

        builder.Entity<RefreshToken>(e =>
        {
            e.ToTable("refresh_tokens");
            e.Property(r => r.Id).HasColumnName("id");
            e.Property(r => r.UserId).HasColumnName("user_id");
            e.Property(r => r.Token).HasColumnName("token").IsRequired();
            e.Property(r => r.ExpiresAt).HasColumnName("expires_at");
            e.Property(r => r.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("NOW()");
            e.HasIndex(r => r.Token).IsUnique();

            e.HasOne(r => r.User)
                .WithMany(u => u.RefreshTokens)
                .HasForeignKey(r => r.UserId)
                .OnDelete(DeleteBehavior.Cascade);
        });
    }
}

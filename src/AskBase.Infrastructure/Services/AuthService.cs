using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using AskBase.Application.DTOs;
using AskBase.Application.Interfaces;
using AskBase.Domain.Entities;
using AskBase.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.IdentityModel.Tokens;

namespace AskBase.Infrastructure.Services;

public class AuthService : IAuthService
{
    private readonly AppDbContext _db;
    private readonly IConfiguration _config;

    public AuthService(AppDbContext db, IConfiguration config)
    {
        _db = db;
        _config = config;
    }

    public async Task<AuthResponse> RegisterAsync(RegisterRequest req)
    {
        if (string.IsNullOrWhiteSpace(req.OrgName))
            throw new ArgumentException("Organization name is required.");
        if (!req.Email.Contains('@'))
            throw new ArgumentException("A valid email address is required.");
        if (req.Password.Length < 8)
            throw new ArgumentException("Password must be at least 8 characters.");

        var emailTaken = await _db.Users
            .IgnoreQueryFilters()
            .AnyAsync(u => u.Email == req.Email.ToLower());

        if (emailTaken)
            throw new ArgumentException("An account with this email already exists.");

        var org = new Organization
        {
            Name = req.OrgName.Trim(),
            Slug = await GenerateUniqueSlugAsync(req.OrgName)
        };
        _db.Organizations.Add(org);

        var user = new User
        {
            OrgId = org.Id,
            Email = req.Email.ToLower().Trim(),
            PasswordHash = BCrypt.Net.BCrypt.HashPassword(req.Password),
            Role = "admin"
        };
        _db.Users.Add(user);

        await _db.SaveChangesAsync();

        return await IssueTokensAsync(user, org);
    }

    public async Task<AuthResponse> LoginAsync(LoginRequest req)
    {
        var user = await _db.Users
            .IgnoreQueryFilters()
            .Include(u => u.Organization)
            .FirstOrDefaultAsync(u => u.Email == req.Email.ToLower());

        if (user == null || !BCrypt.Net.BCrypt.Verify(req.Password, user.PasswordHash))
            throw new UnauthorizedAccessException("Invalid email or password.");

        return await IssueTokensAsync(user, user.Organization);
    }

    public async Task<AuthResponse> RefreshAsync(string refreshToken)
    {
        var stored = await _db.RefreshTokens
            .IgnoreQueryFilters()
            .Include(r => r.User)
                .ThenInclude(u => u.Organization)
            .FirstOrDefaultAsync(r => r.Token == refreshToken);

        if (stored == null || stored.IsExpired)
            throw new UnauthorizedAccessException("Invalid or expired refresh token.");

        _db.RefreshTokens.Remove(stored);

        return await IssueTokensAsync(stored.User, stored.User.Organization);
    }

    public async Task LogoutAsync(string refreshToken)
    {
        var stored = await _db.RefreshTokens
            .IgnoreQueryFilters()
            .FirstOrDefaultAsync(r => r.Token == refreshToken);

        if (stored != null)
        {
            _db.RefreshTokens.Remove(stored);
            await _db.SaveChangesAsync();
        }
    }

    private async Task<AuthResponse> IssueTokensAsync(User user, Organization org)
    {
        var accessToken = BuildJwt(user, org);
        var refreshToken = GenerateRefreshToken();

        var refreshDays = int.TryParse(_config["Jwt:RefreshTokenDays"], out var parsedRefreshDays)
            ? parsedRefreshDays
            : 7;

        _db.RefreshTokens.Add(new RefreshToken
        {
            UserId = user.Id,
            Token = refreshToken,
            ExpiresAt = DateTime.UtcNow.AddDays(refreshDays)
        });

        await _db.SaveChangesAsync();

        return new AuthResponse(
            AccessToken: accessToken,
            RefreshToken: refreshToken,
            UserId: user.Id,
            OrgId: org.Id,
            Email: user.Email,
            Role: user.Role
        );
    }

    private string BuildJwt(User user, Organization org)
    {
        var secret = _config["Jwt:Secret"]
            ?? throw new InvalidOperationException("Jwt:Secret is not configured.");

        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new List<Claim>
        {
            new(JwtRegisteredClaimNames.Sub, user.Id.ToString()),
            new(JwtRegisteredClaimNames.Email, user.Email),
            new(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
            new("tenant_id", org.Id.ToString()),
            new("org_name", org.Name),
            new(ClaimTypes.Role, user.Role),
        };

        var accessMinutes = int.TryParse(_config["Jwt:AccessTokenMinutes"], out var parsedAccessMinutes)
            ? parsedAccessMinutes
            : 15;

        var token = new JwtSecurityToken(
            issuer: _config["Jwt:Issuer"],
            audience: _config["Jwt:Audience"],
            claims: claims,
            expires: DateTime.UtcNow.AddMinutes(accessMinutes),
            signingCredentials: creds
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    private static string GenerateRefreshToken()
    {
        var bytes = new byte[64];
        RandomNumberGenerator.Fill(bytes);
        return Convert.ToBase64String(bytes);
    }

    private async Task<string> GenerateUniqueSlugAsync(string name)
    {
        var baseSlug = Regex.Replace(name.ToLower().Trim(), @"[^a-z0-9s-]", "")
            .Trim()
            .Replace(' ', '-');

        var slug = $"{baseSlug}-{Guid.NewGuid().ToString()[..6]}";

        var exists = await _db.Organizations.AnyAsync(o => o.Slug == slug);
        return exists ? $"{slug}-{Guid.NewGuid().ToString()[..4]}" : slug;
    }
}

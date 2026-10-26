using AskBase.Application.DTOs;
using AskBase.Application.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AskBase.Api.Controllers;

[ApiController]
[Route("api/auth")]
public class AuthController : ControllerBase
{
    private readonly IAuthService _auth;

    public AuthController(IAuthService auth) => _auth = auth;

    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] RegisterRequest request)
    {
        var result = await _auth.RegisterAsync(request);
        return Ok(result);
    }

    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request)
    {
        var result = await _auth.LoginAsync(request);
        return Ok(result);
    }

    [HttpPost("refresh")]
    public async Task<IActionResult> Refresh([FromBody] RefreshRequest request)
    {
        var result = await _auth.RefreshAsync(request.RefreshToken);
        return Ok(result);
    }

    [HttpPost("logout")]
    [Authorize]
    public async Task<IActionResult> Logout([FromBody] RefreshRequest request)
    {
        await _auth.LogoutAsync(request.RefreshToken);
        return Ok(new { message = "Logged out successfully." });
    }

    [HttpGet("me")]
    [Authorize]
    public IActionResult Me() => Ok(new
    {
        userId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value,
        email = User.FindFirst(System.Security.Claims.ClaimTypes.Email)?.Value,
        tenantId = User.FindFirst("tenant_id")?.Value,
        orgName = User.FindFirst("org_name")?.Value,
        role = User.FindFirst(System.Security.Claims.ClaimTypes.Role)?.Value,
    });
}

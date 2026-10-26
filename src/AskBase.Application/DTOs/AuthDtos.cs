namespace AskBase.Application.DTOs;

public record RegisterRequest(
    string OrgName,
    string Email,
    string Password
);

public record LoginRequest(
    string Email,
    string Password
);

public record RefreshRequest(
    string RefreshToken
);

public record AuthResponse(
    string AccessToken,
    string RefreshToken,
    Guid UserId,
    Guid OrgId,
    string Email,
    string Role
);

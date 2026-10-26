using System.Net;
using System.Text.Json;

namespace AskBase.Api.Middleware;

public class GlobalExceptionMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<GlobalExceptionMiddleware> _logger;

    public GlobalExceptionMiddleware(RequestDelegate next, ILogger<GlobalExceptionMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unhandled exception: {Method} {Path}", context.Request.Method, context.Request.Path);
            await WriteErrorAsync(context, ex);
        }
    }

    private static async Task WriteErrorAsync(HttpContext context, Exception ex)
    {
        context.Response.ContentType = "application/json";

        var (status, message) = ex switch
        {
            UnauthorizedAccessException => (HttpStatusCode.Unauthorized, "Unauthorized"),
            ArgumentException e => (HttpStatusCode.BadRequest, e.Message),
            KeyNotFoundException e => (HttpStatusCode.NotFound, e.Message),
            InvalidOperationException e => (HttpStatusCode.Conflict, e.Message),
            _ => (HttpStatusCode.InternalServerError, "An unexpected error occurred.")
        };

        context.Response.StatusCode = (int)status;

        var body = new { error = message, statusCode = (int)status };
        await context.Response.WriteAsync(JsonSerializer.Serialize(body));
    }
}

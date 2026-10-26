namespace AskBase.Domain.Entities;

public class Organization
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    public string Plan { get; set; } = "free";
    public string? StripeCustomerId { get; set; }
    public string? StripeSubscriptionId { get; set; }
    public int SeatsLimit { get; set; } = 25;
    public int SourcesLimit { get; set; } = 3;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public ICollection<User> Users { get; set; } = [];
}

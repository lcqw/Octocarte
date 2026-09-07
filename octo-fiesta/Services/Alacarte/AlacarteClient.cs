using System.Net;
using System.Text.Json;

namespace octo_fiesta.Services.Alacarte;

/// <summary>Only ALACarte's public HTTP API; no Apple credentials or preferences.</summary>
public sealed class AlacarteClient(IHttpClientFactory factory)
{
    public const string ClientName = "alacarte";
    public async Task<JsonElement> GetAsync(string path, CancellationToken ct = default)
    {
        using var response = await factory.CreateClient(ClientName).GetAsync(path, ct);
        response.EnsureSuccessStatusCode();
        using var doc = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(ct), cancellationToken: ct);
        return doc.RootElement.Clone();
    }

    public async Task SubmitAlbumAsync(string albumId, CancellationToken ct)
    {
        // Omitting storefront and quality is intentional: ALACarte owns preferences.
        using var response = await factory.CreateClient(ClientName).PostAsJsonAsync("api/download", new { albumId }, ct);
        if (response.StatusCode == HttpStatusCode.Conflict) return; // already owned
        response.EnsureSuccessStatusCode();
    }
}

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

    public Task SubmitAlbumAsync(string albumId, CancellationToken ct) =>
        SubmitAsync("api/download", new { albumId }, ct);

    public Task SubmitSongAsync(string songId, CancellationToken ct) =>
        SubmitAsync("api/download/song", new { songId }, ct);

    private async Task SubmitAsync(string path, object body, CancellationToken ct)
    {
        // Omitting storefront and quality is intentional: ALACarte owns preferences.
        var client = factory.CreateClient(ClientName);
        using var request = new HttpRequestMessage(HttpMethod.Post, path)
        {
            Content = JsonContent.Create(body)
        };
        // ALACarte originGuard requires matching Origin/Host on authenticated writes.
        request.Headers.Add("Origin", client.BaseAddress!.GetLeftPart(UriPartial.Authority));
        using var response = await client.SendAsync(request, ct);
        if (response.StatusCode == HttpStatusCode.Conflict) return; // already owned
        response.EnsureSuccessStatusCode();
    }
}

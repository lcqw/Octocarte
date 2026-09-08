using System.Collections.Concurrent;
using System.Threading.Channels;

namespace octo_fiesta.Services.Alacarte;

/// <summary>Bounded, request-independent work; ALACarte owns persistent deduplication.</summary>
public sealed class AlbumAcquisitionService(AlacarteClient api, IMusicMetadataService metadata,
    ILogger<AlbumAcquisitionService> logger, IConfiguration configuration) : BackgroundService
{
    private readonly bool downloadWholeAlbum = configuration.GetValue("Alacarte:DownloadWholeAlbum", true);
    private readonly Channel<string> queue = Channel.CreateBounded<string>(new BoundedChannelOptions(256) { SingleReader = true });
    private readonly ConcurrentDictionary<string, byte> pending = new();
    private readonly Dictionary<string, DateTimeOffset> recentRequests = new();
    public bool TryQueueSong(string id)
    {
        if (!pending.TryAdd(id, 0)) return true;
        if (queue.Writer.TryWrite(id)) return true;
        pending.TryRemove(id, out _);
        logger.LogWarning("Apple acquisition queue is full");
        return false;
    }
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await foreach (var id in queue.Reader.ReadAllAsync(stoppingToken))
        {
            try
            {
                if (!downloadWholeAlbum)
                {
                    await SubmitOnceAsync(id, () => api.SubmitSongAsync(id, stoppingToken));
                    continue;
                }
                var song = await metadata.GetSongAsync("apple", id);
                var albumId = song?.AlbumId;
                if (albumId?.StartsWith("ext-apple-album-", StringComparison.Ordinal) == true) albumId = albumId[16..];
                if (string.IsNullOrEmpty(albumId))
                {
                    var result = await api.GetAsync($"api/search?q={Uri.EscapeDataString($"https://music.apple.com/song/{id}")}", stoppingToken);
                    var album = AlacarteMetadataService.Items(result, "albums").FirstOrDefault();
                    if (album.ValueKind == System.Text.Json.JsonValueKind.Object) albumId = AlacarteMetadataService.Text(album, "id");
                }
                if (string.IsNullOrEmpty(albumId)) { logger.LogWarning("Apple parent album could not be resolved"); continue; }
                await SubmitOnceAsync(albumId, () => api.SubmitAlbumAsync(albumId, stoppingToken));
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (HttpRequestException ex) { logger.LogWarning("ALACarte download submission failed (HTTP {Status}); a later play may retry", (int?)ex.StatusCode); }
            catch (Exception) { logger.LogWarning("ALACarte download submission failed; a later play may retry"); }
            finally { pending.TryRemove(id, out _); }
        }
    }

    private async Task SubmitOnceAsync(string id, Func<Task> submit)
    {
        var now = DateTimeOffset.UtcNow;
        foreach (var key in recentRequests.Where(p => p.Value <= now).Select(p => p.Key).ToArray()) recentRequests.Remove(key);
        if (recentRequests.ContainsKey(id)) return;
        // One worker debounces only the requested album or song. ALACarte owns
        // persistent duplicate detection and decides what is missing.
        await submit();
        recentRequests[id] = DateTimeOffset.UtcNow.AddSeconds(30);
    }
}

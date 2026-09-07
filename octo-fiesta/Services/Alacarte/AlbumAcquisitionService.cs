using System.Collections.Concurrent;
using System.Threading.Channels;

namespace octo_fiesta.Services.Alacarte;

/// <summary>Bounded, request-independent work; ALACarte owns persistent deduplication.</summary>
public sealed class AlbumAcquisitionService(AlacarteClient api, IMusicMetadataService metadata,
    ILogger<AlbumAcquisitionService> logger) : BackgroundService
{
    private readonly Channel<string> queue = Channel.CreateBounded<string>(new BoundedChannelOptions(256) { SingleReader = true });
    private readonly ConcurrentDictionary<string, byte> pending = new();
    private readonly Dictionary<string, DateTimeOffset> recentAlbums = new();
    public bool TryQueueSong(string id)
    {
        if (!pending.TryAdd(id, 0)) return true;
        if (queue.Writer.TryWrite(id)) return true;
        pending.TryRemove(id, out _);
        logger.LogWarning("Album acquisition queue is full");
        return false;
    }
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await foreach (var id in queue.Reader.ReadAllAsync(stoppingToken))
        {
            try
            {
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
                var now = DateTimeOffset.UtcNow;
                foreach (var key in recentAlbums.Where(p => p.Value <= now).Select(p => p.Key).ToArray()) recentAlbums.Remove(key);
                if (recentAlbums.ContainsKey(albumId)) continue;
                // One worker serializes requests across tracks in the same album. Do not
                // mirror ALACarte's queue/history/library: it decides what is missing.
                await api.SubmitAlbumAsync(albumId, stoppingToken);
                recentAlbums[albumId] = now.AddSeconds(30);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (HttpRequestException ex) { logger.LogWarning("ALACarte album submission failed (HTTP {Status}); a later play may retry", (int?)ex.StatusCode); }
            catch (Exception) { logger.LogWarning("ALACarte album submission failed; a later play may retry"); }
            finally { pending.TryRemove(id, out _); }
        }
    }
}

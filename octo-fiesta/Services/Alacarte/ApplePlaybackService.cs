using octo_fiesta.Services.YouTube;

namespace octo_fiesta.Services.Alacarte;

public sealed class ApplePlaybackService(IMusicMetadataService metadata, YouTubeResolver youtube, AlbumAcquisitionService acquisition)
{
    public async Task<DirectStreamInfo?> OpenAsync(string id, string? range, CancellationToken ct)
    {
        var song = await metadata.GetSongAsync("apple", id);
        if (song is null) return null;
        // No awaited acquisition task on the playback path. Parent lookup and POST
        // run in the hosted worker with application lifetime, not client lifetime.
        acquisition.TryQueueSong(id);
        var hit = await youtube.SearchAsync($"{song.Artist} - {song.Title}", song.Duration, ct: ct);
        if (hit is null) return null;
        var opened = await youtube.OpenStreamAsync(hit.VideoId, range, ct);
        if (opened is not { } stream) return null;
        return new DirectStreamInfo { AudioStream = stream.stream, Owner = stream.owner,
            ContentType = stream.contentType, ContentLength = stream.contentLength,
            StatusCode = stream.statusCode, ContentRange = stream.contentRange };
    }
}

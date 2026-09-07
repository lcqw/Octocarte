using octo_fiesta.Models.Download;

namespace octo_fiesta.Services.Alacarte;

/// <summary>Apple acquisition is exclusively owned by the independent ALACarte service.</summary>
public sealed class AlacarteDownloadService : IDownloadService
{
    private static NotSupportedException Unsupported() => new("Apple acquisition uses ALACarte whole-album jobs; direct file downloading is unavailable.");
    public Task<string> DownloadSongAsync(string externalProvider, string externalId, CancellationToken cancellationToken = default) => Task.FromException<string>(Unsupported());
    public Task<string> DownloadSongToPermanentAsync(string externalProvider, string externalId, CancellationToken cancellationToken = default) => Task.FromException<string>(Unsupported());
    public Task<(Stream Stream, string FilePath)> DownloadAndStreamAsync(string externalProvider, string externalId, CancellationToken cancellationToken = default) => Task.FromException<(Stream, string)>(Unsupported());
    public void UpgradeQualityInBackground(string externalProvider, string externalId) { }
    public void DownloadRemainingAlbumTracksInBackground(string externalProvider, string albumExternalId, string excludeTrackExternalId) { }
    public void DownloadFullAlbumInBackground(string externalProvider, string albumExternalId) { }
    public void DownloadFullAlbumInBackgroundToPermanent(string externalProvider, string albumExternalId) { }
    public DownloadInfo? GetDownloadStatus(string songId) => null;
    public Task<string?> GetLocalPathIfExistsAsync(string externalProvider, string externalId, CancellationToken cancellationToken = default) => Task.FromResult<string?>(null);
    public Task<bool> PermanentizeCachedSongAsync(string externalProvider, string externalId, CancellationToken cancellationToken = default) => Task.FromResult(false);
    public Task<bool> IsAvailableAsync() => Task.FromResult(true);
}

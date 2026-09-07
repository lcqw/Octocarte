using octo_fiesta.Models.Subsonic;
using System.Text.Json;
using Microsoft.Extensions.Caching.Memory;
using octo_fiesta.Models.Domain;
using octo_fiesta.Models.Search;

namespace octo_fiesta.Services.Alacarte;

public sealed class AlacarteMetadataService(AlacarteClient api) : IMusicMetadataService, IDisposable
{
    private readonly MemoryCache songs = new(new MemoryCacheOptions { SizeLimit = 10000 });
    internal static string? Text(JsonElement e, string key) => e.TryGetProperty(key, out var v) && v.ValueKind != JsonValueKind.Null ? v.ToString() : null;
    internal static int? Number(JsonElement e, string key) => int.TryParse(Text(e, key), out var n) ? n : null;
    internal static IEnumerable<JsonElement> Items(JsonElement e, string key) => e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.Array ? v.EnumerateArray() : [];
    private static string? External(string type, string? id) => string.IsNullOrEmpty(id) ? null : $"ext-apple-{type}-{id}";
    private static string? Artwork(JsonElement e) => Text(e, "artworkTemplate")?.Replace("{w}", "600").Replace("{h}", "600").Replace("{f}", "jpg");
    private Song MapSong(JsonElement e, Album? album = null)
    {
        var song = new Song {
            ExternalProvider = "apple", ExternalId = Text(e, "id"), Title = Text(e, "name") ?? "",
            Artist = Text(e, "artistName") ?? album?.Artist ?? "", ArtistId = External("artist", Text(e, "artistId")) ?? album?.ArtistId,
            Album = Text(e, "albumName") ?? album?.Title ?? "", AlbumId = External("album", Text(e, "albumId")) ?? album?.Id,
            Duration = Number(e, "durationMs") / 1000, Track = Number(e, "trackNumber"), DiscNumber = Number(e, "discNumber"),
            Isrc = Text(e, "isrc"), CoverArtUrl = Artwork(e) ?? album?.CoverArtUrl, Year = album?.Year,
        };
        if (song.ExternalId is not null) songs.Set(song.ExternalId, song, new MemoryCacheEntryOptions().SetSize(1).SetSlidingExpiration(TimeSpan.FromHours(6)));
        return song;
    }
    private Album MapAlbum(JsonElement e)
    {
        var id = Text(e, "id") ?? "";
        var album = new Album { Id = $"ext-apple-album-{id}", ExternalProvider = "apple", ExternalId = id,
            Title = Text(e, "name") ?? "", Artist = Text(e, "artistName") ?? "", ArtistId = External("artist", Text(e, "artistId")),
            Year = Number(e, "year"), SongCount = Number(e, "trackCount"), CoverArtUrl = Artwork(e) };
        album.Songs = Items(e, "tracks").Select(t => MapSong(t, album)).ToList();
        return album;
    }
    private static Artist MapArtist(JsonElement e) { var id = Text(e, "id") ?? ""; return new Artist {
        Id = $"ext-apple-artist-{id}", ExternalProvider = "apple", ExternalId = id, Name = Text(e, "name") ?? "" }; }
    public async Task<SearchResult> SearchAllAsync(string query, int songLimit = 20, int albumLimit = 20, int artistLimit = 20)
    {
        var limit = Math.Clamp(Math.Max(songLimit, Math.Max(albumLimit, artistLimit)), 1, 50);
        var data = await api.GetAsync($"api/search?q={Uri.EscapeDataString(query)}&limit={limit}&types=songs,albums,artists");
        return new SearchResult { Songs = Items(data, "songs").Take(Math.Max(0, songLimit)).Select(t => MapSong(t)).ToList(),
            Albums = Items(data, "albums").Take(Math.Max(0, albumLimit)).Select(MapAlbum).ToList(),
            Artists = Items(data, "artists").Take(Math.Max(0, artistLimit)).Select(MapArtist).ToList() };
    }
    public async Task<List<Song>> SearchSongsAsync(string query, int limit = 20) => (await SearchAllAsync(query, limit, 0, 0)).Songs;
    public async Task<List<Album>> SearchAlbumsAsync(string query, int limit = 20) => (await SearchAllAsync(query, 0, limit, 0)).Albums;
    public async Task<List<Artist>> SearchArtistsAsync(string query, int limit = 20) => (await SearchAllAsync(query, 0, 0, limit)).Artists;
    public async Task<Song?> GetSongAsync(string externalProvider, string externalId)
    {
        if (externalProvider != "apple") return null;
        if (songs.TryGetValue<Song>(externalId, out var song)) return song;
        // ALACarte exposes song detail through its song-link search, which resolves the album.
        var result = await api.GetAsync($"api/search?q={Uri.EscapeDataString($"https://music.apple.com/song/{externalId}")}");
        var parent = Items(result, "albums").FirstOrDefault();
        if (parent.ValueKind == JsonValueKind.Undefined) return null;
        var album = await GetAlbumAsync("apple", Text(parent, "id")!);
        return album?.Songs.FirstOrDefault(t => t.ExternalId == externalId);
    }
    public async Task<Album?> GetAlbumAsync(string externalProvider, string externalId)
    {
        if (externalProvider != "apple") return null;
        var data = await api.GetAsync($"api/album/{Uri.EscapeDataString(externalId)}");
        return data.TryGetProperty("album", out var album) ? MapAlbum(album) : null;
    }
    public async Task<Artist?> GetArtistAsync(string externalProvider, string externalId)
    {
        if (externalProvider != "apple") return null;
        var data = await api.GetAsync($"api/artist/{Uri.EscapeDataString(externalId)}");
        return data.TryGetProperty("artist", out var artist) ? MapArtist(artist) : null;
    }
    public async Task<List<Album>> GetArtistAlbumsAsync(string externalProvider, string externalId)
    {
        if (externalProvider != "apple") return [];
        return Items(await api.GetAsync($"api/artist/{Uri.EscapeDataString(externalId)}"), "albums").Select(MapAlbum).ToList();
    }
    public Task<List<ExternalPlaylist>> SearchPlaylistsAsync(string query, int limit = 20) => Task.FromResult(new List<ExternalPlaylist>());
    public Task<ExternalPlaylist?> GetPlaylistAsync(string externalProvider, string externalId) => Task.FromResult<ExternalPlaylist?>(null);
    public Task<List<Song>> GetPlaylistTracksAsync(string externalProvider, string externalId) => Task.FromResult(new List<Song>());
    public void Dispose() => songs.Dispose();
}

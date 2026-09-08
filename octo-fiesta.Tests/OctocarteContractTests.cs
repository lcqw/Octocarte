using System.Net;
using System.Text;
using System.Text.Json;
using System.Xml.Linq;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using octo_fiesta.Models.Domain;
using octo_fiesta.Services;
using octo_fiesta.Services.Alacarte;
using octo_fiesta.Services.Subsonic;
using octo_fiesta.Services.YouTube;

namespace octo_fiesta.Tests;

public class OctocarteContractTests
{
    private sealed class Handler(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct) => send(request, ct);
    }
    private static IHttpClientFactory Factory(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send)
    {
        var factory = new Mock<IHttpClientFactory>();
        factory.Setup(f => f.CreateClient(It.IsAny<string>())).Returns(() => new HttpClient(new Handler(send)) { BaseAddress = new Uri("http://fixture/") });
        return factory.Object;
    }
    private static HttpResponseMessage Json(string json, HttpStatusCode status = HttpStatusCode.OK) => new(status) { Content = new StringContent(json, Encoding.UTF8, "application/json") };

    [Fact]
    public async Task CatalogMappingUsesTemporaryM4aInJsonAndXml()
    {
        var api = new AlacarteClient(Factory((req, ct) => {
            Assert.DoesNotContain("storefront", req.RequestUri!.Query);
            return Task.FromResult(Json("""{"songs":[{"id":"42","name":"Song","artistName":"Artist","albumName":"Album","albumId":"7","durationMs":123000,"isrc":"TEST"}],"albums":[],"artists":[]}"""));
        }));
        using var metadata = new AlacarteMetadataService(api);
        var song = Assert.Single(await metadata.SearchSongsAsync("Song"));
        Assert.Equal("ext-apple-album-7", song.AlbumId);
        Assert.Equal(123, song.Duration);
        var builder = new SubsonicResponseBuilder();
        var json = builder.ConvertSongToJson(song);
        Assert.Equal("ext-apple-song-42", json["id"]);
        Assert.Equal("m4a", json["suffix"]);
        Assert.Equal("audio/mp4", json["contentType"]);
        Assert.Equal(0, json["bitRate"]);
        Assert.False(json.ContainsKey("bitDepth"));
        var xml = builder.ConvertSongToXml(song, XNamespace.None);
        Assert.Equal("m4a", xml.Attribute("suffix")!.Value);
        Assert.Equal("audio/mp4", xml.Attribute("contentType")!.Value);
    }

    [Fact]
    public async Task CatalogOutageDoesNotBreakLocalSearchMerging()
    {
        using var metadata = new AlacarteMetadataService(new AlacarteClient(Factory((req, ct) =>
            Task.FromResult(Json("{}", HttpStatusCode.ServiceUnavailable)))));
        var result = await metadata.SearchAllAsync("Song");
        Assert.Empty(result.Songs);
        Assert.Empty(result.Albums);
    }

    [Fact]
    public void TemporaryTranscodeDecisionAdvertisesAac()
    {
        var response = (JsonResult)new SubsonicResponseBuilder().CreateTranscodeDecisionResponse(
            new Song { ExternalProvider = "apple" }, "http");
        using var json = JsonDocument.Parse(JsonSerializer.Serialize(response.Value));
        var stream = json.RootElement.GetProperty("subsonic-response").GetProperty("transcodeDecision").GetProperty("sourceStream");
        Assert.Equal("m4a", stream.GetProperty("container").GetString());
        Assert.Equal("aac", stream.GetProperty("codec").GetString());
    }

    [Fact]
    public async Task ColdSongLookupUsesAlacarteSongLinkAndAlbum()
    {
        using var metadata = new AlacarteMetadataService(new AlacarteClient(Factory((req, ct) => Task.FromResult(
            req.RequestUri!.AbsolutePath == "/api/album/7"
                ? Json("""{"album":{"id":"7","name":"Album","artistName":"Artist","tracks":[{"id":"42","name":"Song","durationMs":1000}]}}""")
                : Json("""{"albums":[{"id":"7"}]}""")))));
        var song = await metadata.GetSongAsync("apple", "42");
        Assert.NotNull(song);
        Assert.Equal("ext-apple-album-7", song.AlbumId);
        Assert.Equal("Album", song.Album);
    }

    [Theory]
    [InlineData(200, null)]
    [InlineData(206, "bytes 0-1/100")]
    [InlineData(416, "bytes */100")]
    public async Task ResolverAndResultPreserveRangeStatusHeadersAndBody(int status, string? contentRange)
    {
        var factory = Factory((req, ct) => {
            Assert.Equal("bytes=0-1", req.Headers.Range!.ToString());
            var response = new HttpResponseMessage((HttpStatusCode)status) { Content = new ByteArrayContent([1, 2]) };
            response.Content.Headers.ContentType = new("audio/mp4");
            if (contentRange is not null) response.Content.Headers.TryAddWithoutValidation("Content-Range", contentRange);
            return Task.FromResult(response);
        });
        var resolver = new YouTubeResolver(factory, new ConfigurationBuilder().Build(), NullLogger<YouTubeResolver>.Instance);
        var opened = await resolver.OpenStreamAsync("video", "bytes=0-1");
        Assert.NotNull(opened);
        var s = opened.Value;
        var result = new DirectStreamInfo { AudioStream = s.stream, Owner = s.owner, ContentType = s.contentType,
            ContentLength = s.contentLength, StatusCode = s.statusCode, ContentRange = s.contentRange };
        var context = new DefaultHttpContext(); context.Response.Body = new MemoryStream();
        await result.ExecuteResultAsync(new ActionContext { HttpContext = context });
        Assert.Equal(status, context.Response.StatusCode);
        Assert.Equal(contentRange ?? "", context.Response.Headers.ContentRange.ToString());
        Assert.Equal("bytes", context.Response.Headers.AcceptRanges.ToString());
        Assert.Equal(2, context.Response.ContentLength);
        Assert.Equal(new byte[] { 1, 2 }, ((MemoryStream)context.Response.Body).ToArray());
    }

    [Theory]
    [InlineData(null)]
    [InlineData("true")]
    [InlineData("false")]
    public async Task PlaybackDoesNotWaitForDownloadAndDeduplicatesAtConfiguredScope(string? wholeAlbum)
    {
        var singleSong = wholeAlbum == "false";
        var postStarted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var releasePost = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var barrier = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var replayBarrier = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var posts = new System.Collections.Concurrent.ConcurrentQueue<string>();
        var factory = Factory(async (req, ct) => {
            if (req.RequestUri!.AbsolutePath.StartsWith("/api/download")) {
                Assert.Equal(singleSong ? "/api/download/song" : "/api/download", req.RequestUri.AbsolutePath);
                Assert.Equal("http://fixture", Assert.Single(req.Headers.GetValues("Origin")));
                using var body = JsonDocument.Parse(await req.Content!.ReadAsStringAsync(ct));
                var property = Assert.Single(body.RootElement.EnumerateObject());
                Assert.Equal(singleSong ? "songId" : "albumId", property.Name);
                var id = property.Value.GetString()!;
                if (id == (singleSong ? "44" : "8")) { barrier.TrySetResult(); return Json("{}", HttpStatusCode.Conflict); }
                if (id == (singleSong ? "45" : "9")) { replayBarrier.TrySetResult(); return Json("{}", HttpStatusCode.Conflict); }
                posts.Enqueue(id);
                postStarted.TrySetResult();
                await releasePost.Task.WaitAsync(ct);
                return Json("{}", HttpStatusCode.Conflict);
            }
            if (req.RequestUri.AbsolutePath == "/search") return Json("""{"video_id":"video"}""");
            return new HttpResponseMessage(HttpStatusCode.OK) { Content = new ByteArrayContent([1, 2]) };
        });
        var metadata = new Mock<IMusicMetadataService>();
        metadata.Setup(m => m.GetSongAsync("apple", It.IsAny<string>())).ReturnsAsync(new Song { Title = "Song", Artist = "Artist", AlbumId = "ext-apple-album-7" });
        metadata.Setup(m => m.GetSongAsync("apple", "44")).ReturnsAsync(new Song { AlbumId = "ext-apple-album-8" });
        metadata.Setup(m => m.GetSongAsync("apple", "45")).ReturnsAsync(new Song { AlbumId = "ext-apple-album-9" });
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?> {
            ["Alacarte:DownloadWholeAlbum"] = wholeAlbum
        }).Build();
        using var worker = new AlbumAcquisitionService(new AlacarteClient(factory), metadata.Object, NullLogger<AlbumAcquisitionService>.Instance, configuration);
        await worker.StartAsync(default);
        try {
            var playback = new ApplePlaybackService(metadata.Object, new YouTubeResolver(factory, new ConfigurationBuilder().Build(), NullLogger<YouTubeResolver>.Instance), worker);
            var stream = await playback.OpenAsync("42", null, default).WaitAsync(TimeSpan.FromSeconds(2));
            Assert.NotNull(stream);
            stream.Owner.Dispose();
            await postStarted.Task.WaitAsync(TimeSpan.FromSeconds(2));
            for (int i = 0; i < 20; i++) Assert.True(worker.TryQueueSong("42"));
            Assert.True(worker.TryQueueSong("43")); // same parent, different track
            releasePost.TrySetResult();
            Assert.True(worker.TryQueueSong("44")); // barrier after both requested tracks
            await barrier.Task.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(singleSong ? new[] { "42", "43" } : new[] { "7" }, posts.ToArray());
            // A replay after the first POST completes is still debounced (including 409).
            worker.TryQueueSong("42");
            worker.TryQueueSong("45");
            await replayBarrier.Task.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(singleSong ? 2 : 1, posts.Count);
        }
        finally { releasePost.TrySetResult(); await worker.StopAsync(default); }
    }

    [Fact]
    public async Task FailedSongSubmissionCanRetryWithoutResolvingAnAlbumInOctocarte()
    {
        var attempts = 0;
        var firstBarrier = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var lastBarrier = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var factory = Factory(async (req, ct) => {
            Assert.Equal("/api/download/song", req.RequestUri!.AbsolutePath);
            using var body = JsonDocument.Parse(await req.Content!.ReadAsStringAsync(ct));
            var id = body.RootElement.GetProperty("songId").GetString();
            if (id == "43") firstBarrier.TrySetResult();
            if (id == "44") lastBarrier.TrySetResult();
            if (id == "42" && Interlocked.Increment(ref attempts) == 1) return Json("{}", HttpStatusCode.ServiceUnavailable);
            return Json("{}", HttpStatusCode.Accepted);
        });
        var metadata = new Mock<IMusicMetadataService>(MockBehavior.Strict);
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?> {
            ["Alacarte:DownloadWholeAlbum"] = "false"
        }).Build();
        using var worker = new AlbumAcquisitionService(new AlacarteClient(factory), metadata.Object, NullLogger<AlbumAcquisitionService>.Instance, config);
        await worker.StartAsync(default);
        try {
            worker.TryQueueSong("42"); worker.TryQueueSong("43");
            await firstBarrier.Task.WaitAsync(TimeSpan.FromSeconds(2));
            worker.TryQueueSong("42"); worker.TryQueueSong("44");
            await lastBarrier.Task.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(2, attempts);
            metadata.VerifyNoOtherCalls();
        }
        finally { await worker.StopAsync(default); }
    }

    [Fact]
    public async Task ArtistInfoAndDiscographyShareOneRequestAndExposeArtwork()
    {
        var calls = 0;
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        using var metadata = new AlacarteMetadataService(new AlacarteClient(Factory(async (req, ct) => {
            Assert.Equal("/api/artist/9", req.RequestUri!.AbsolutePath);
            Interlocked.Increment(ref calls);
            await release.Task;
            return Json("""{"artist":{"id":"9","name":"Artist","artworkTemplate":"https://images.example/{w}x{h}bb.jpg"},"albums":[{"id":"7","name":"Album"}]}""");
        })));
        var artistTask = metadata.GetArtistAsync("apple", "9");
        var albumsTask = metadata.GetArtistAlbumsAsync("apple", "9");
        release.SetResult();
        var artist = await artistTask;
        Assert.NotNull(artist);
        Assert.Single(await albumsTask);
        Assert.Equal(1, artist.AlbumCount);
        Assert.Equal("https://images.example/600x600bb.jpg", artist.ImageUrl);
        await metadata.GetArtistAsync("apple", "9");
        Assert.Equal(1, calls);
        var builder = new SubsonicResponseBuilder();
        var json = (JsonResult)builder.CreateArtistInfoResponse("json", "artistInfo2", artist);
        using var document = JsonDocument.Parse(JsonSerializer.Serialize(json.Value));
        Assert.Equal(artist.ImageUrl, document.RootElement.GetProperty("subsonic-response").GetProperty("artistInfo2").GetProperty("largeImageUrl").GetString());
        var xml = (ContentResult)builder.CreateArtistInfoResponse("xml", "artistInfo", artist);
        var ns = XNamespace.Get("http://subsonic.org/restapi");
        Assert.Equal(artist.ImageUrl, XDocument.Parse(xml.Content!).Root!.Element(ns + "artistInfo")!.Element(ns + "smallImageUrl")!.Value);
        var searchArtist = new Artist { Id = artist.Id, ExternalProvider = "apple" };
        using var searchJson = JsonDocument.Parse(JsonSerializer.Serialize(builder.ConvertArtistToJson(searchArtist)));
        Assert.Equal(artist.Id, searchJson.RootElement.GetProperty("coverArt").GetString());
        Assert.Equal(artist.Id, builder.ConvertArtistToXml(searchArtist, ns).Attribute("coverArt")!.Value);
    }

    [Fact]
    public async Task FailedArtistRequestCanRetry()
    {
        var calls = 0;
        using var metadata = new AlacarteMetadataService(new AlacarteClient(Factory((req, ct) => Task.FromResult(
            ++calls == 1 ? Json("{}", HttpStatusCode.ServiceUnavailable) : Json("""{"artist":{"id":"9","name":"Artist"},"albums":[]}""")))));
        await Assert.ThrowsAsync<HttpRequestException>(() => metadata.GetArtistAsync("apple", "9"));
        Assert.NotNull(await metadata.GetArtistAsync("apple", "9"));
        Assert.Equal(2, calls);
    }

    [Fact]
    public async Task TopSongsUseRankedEndpointCacheAndOriginalAlbumIds()
    {
        var calls = 0;
        using var metadata = new AlacarteMetadataService(new AlacarteClient(Factory((req, ct) => {
            calls++;
            Assert.Equal("/api/artist/9/top-songs", req.RequestUri!.AbsolutePath);
            Assert.Equal("?limit=50", req.RequestUri.Query);
            return Task.FromResult(Json("""{"songs":[{"id":"42","name":"First","artistName":"Artist","albumId":"7"},{"id":"43","name":"Second","artistName":"Artist","albumId":"8"}]}"""));
        })));
        var songs = await metadata.GetArtistTopSongsAsync("9", 1);
        Assert.Equal("ext-apple-album-7", Assert.Single(songs!).AlbumId);
        Assert.Equal(2, (await metadata.GetArtistTopSongsAsync("9", 50))!.Count);
        Assert.Equal(1, calls);
        Assert.Equal("First", (await metadata.GetSongAsync("apple", "42"))!.Title);
    }

    [Theory]
    [InlineData(404)]
    [InlineData(502)]
    public async Task MissingTopSongsEndpointFallsBack(int status)
    {
        using var metadata = new AlacarteMetadataService(new AlacarteClient(Factory((req, ct) => Task.FromResult(Json("{}", (HttpStatusCode)status)))));
        Assert.Null(await metadata.GetArtistTopSongsAsync("9", 50));
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void RankedSongsKeepOrderAndNativeMetadata(bool json)
    {
        var builder = new SubsonicResponseBuilder();
        var mapper = new SubsonicModelMapper(builder, NullLogger<SubsonicModelMapper>.Instance);
        var ns = XNamespace.Get("http://subsonic.org/restapi");
        object local = json ? new Dictionary<string, object> { ["id"] = "local-43", ["title"] = "Second", ["artist"] = "Artist", ["bitDepth"] = 24 }
            : new XElement(ns + "song", new XAttribute("id", "local-43"), new XAttribute("title", "Second"), new XAttribute("artist", "Artist"), new XAttribute("bitDepth", 24));
        var ranked = new List<Song> { new() { ExternalProvider = "apple", ExternalId = "42", Title = "First", Artist = "Artist" }, new() { ExternalProvider = "apple", ExternalId = "43", Title = "Second", Artist = "Artist" } };
        var result = mapper.MergeRankedSongs([local], ranked, json);
        Assert.Equal(2, result.Count);
        Assert.Same(local, result[1]);
        if (json)
        {
            using var doc = JsonDocument.Parse(JsonSerializer.Serialize(((JsonResult)builder.CreateTopSongsResponse("json", result)).Value));
            var songs = doc.RootElement.GetProperty("subsonic-response").GetProperty("topSongs").GetProperty("song");
            Assert.Equal("ext-apple-song-42", songs[0].GetProperty("id").GetString());
            Assert.Equal(24, songs[1].GetProperty("bitDepth").GetInt32());
        }
        else
        {
            var doc = XDocument.Parse(((ContentResult)builder.CreateTopSongsResponse("xml", result)).Content!);
            var songs = doc.Root!.Element(ns + "topSongs")!.Elements(ns + "song").ToList();
            Assert.Equal("ext-apple-song-42", songs[0].Attribute("id")!.Value);
            Assert.Equal("24", songs[1].Attribute("bitDepth")!.Value);
        }
    }

    [Fact]
    public async Task AlreadyPresentIsSuccessfulNoOp()
    {
        var api = new AlacarteClient(Factory((req, ct) => Task.FromResult(Json("""{"code":"ALREADY_IN_LIBRARY"}""", HttpStatusCode.Conflict))));
        await api.SubmitAlbumAsync("7", default);
    }
}

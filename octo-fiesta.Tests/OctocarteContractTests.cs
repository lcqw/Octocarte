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

    [Fact]
    public async Task PlaybackDoesNotWaitForAlbumPostAndBurstRequestsDeduplicate()
    {
        var postStarted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var releasePost = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var posts = 0;
        var factory = Factory(async (req, ct) => {
            if (req.RequestUri!.AbsolutePath == "/api/download") {
                Interlocked.Increment(ref posts);
                Assert.Equal("{\"albumId\":\"7\"}", await req.Content!.ReadAsStringAsync(ct));
                postStarted.TrySetResult();
                await releasePost.Task.WaitAsync(ct);
                return Json("{}", HttpStatusCode.Conflict);
            }
            if (req.RequestUri.AbsolutePath == "/search") return Json("""{"video_id":"video"}""");
            return new HttpResponseMessage(HttpStatusCode.OK) { Content = new ByteArrayContent([1, 2]) };
        });
        var metadata = new Mock<IMusicMetadataService>();
        metadata.Setup(m => m.GetSongAsync("apple", It.IsAny<string>())).ReturnsAsync(new Song { Title = "Song", Artist = "Artist", AlbumId = "ext-apple-album-7" });
        using var worker = new AlbumAcquisitionService(new AlacarteClient(factory), metadata.Object, NullLogger<AlbumAcquisitionService>.Instance);
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
            // Barrier: a subsequent distinct album is processed only after the first album.
            var next = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            metadata.Setup(m => m.GetSongAsync("apple", "barrier")).Returns(() => { next.TrySetResult(); return Task.FromResult<Song?>(null); });
            worker.TryQueueSong("barrier");
            await next.Task.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(1, posts);
        }
        finally { releasePost.TrySetResult(); await worker.StopAsync(default); }
    }

    [Fact]
    public async Task AlreadyPresentIsSuccessfulNoOp()
    {
        var api = new AlacarteClient(Factory((req, ct) => Task.FromResult(Json("""{"code":"ALREADY_IN_LIBRARY"}""", HttpStatusCode.Conflict))));
        await api.SubmitAlbumAsync("7", default);
    }
}

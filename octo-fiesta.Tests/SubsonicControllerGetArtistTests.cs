using System.Net;
using System.Text.Json;
using System.Xml.Linq;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Moq;
using Moq.Protected;
using octo_fiesta.Controllers;
using octo_fiesta.Models.Domain;
using octo_fiesta.Models.Settings;
using octo_fiesta.Services;
using octo_fiesta.Services.Local;
using octo_fiesta.Services.Subsonic;

namespace octo_fiesta.Tests;

public class SubsonicControllerGetArtistTests
{
    private const string NavidromeArtistJson =
        "{\"subsonic-response\":{\"status\":\"ok\",\"artist\":{\"id\":\"local-artist-id\",\"name\":\"Genesis\",\"albumCount\":1," +
        "\"album\":[{\"id\":\"local-album-1\",\"name\":\"We Can't Dance\"}]}}}";

    private const string NavidromeArtistXml =
        "<subsonic-response status=\"ok\" version=\"1.16.1\" xmlns=\"http://subsonic.org/restapi\">" +
        "<artist id=\"local-artist-id\" name=\"Genesis\" albumCount=\"1\" sortName=\"genesis\">" +
        "<album id=\"local-album-1\" name=\"We Can't Dance\" songCount=\"12\" playCount=\"3\" />" +
        "</artist></subsonic-response>";

    private const string EmptyNavidromeSearchJson =
        "{\"subsonic-response\":{\"status\":\"ok\",\"searchResult3\":{}}}";

    private const string NavidromeSearchArtistJson =
        "{\"subsonic-response\":{\"status\":\"ok\",\"searchResult3\":{\"artist\":[" +
        "{\"id\":\"other-artist-id\",\"name\":\"Genesis Tribute\",\"albumCount\":9}," +
        "{\"id\":\"local-artist-id\",\"name\":\"Genesis\",\"albumCount\":1}]}}}";

    private static SubsonicController CreateController(
        Mock<IMusicMetadataService> metadataServiceMock,
        string requestedId = "local-artist-id",
        (bool IsExternal, string? Provider, string? ExternalId) parsedId = default,
        string? navidromeSearchJson = null,
        bool navidromeXml = false, bool alacarte = false)
    {
        var requestParser = new SubsonicRequestParser();
        var responseBuilder = new SubsonicResponseBuilder();
        var modelMapper = new SubsonicModelMapper(
            responseBuilder,
            new Mock<ILogger<SubsonicModelMapper>>().Object);

        var settings = Options.Create(new SubsonicSettings { Url = "http://localhost:4533", MusicService = alacarte ? MusicService.Alacarte : MusicService.Deezer });

        var mockHttpHandler = new Mock<HttpMessageHandler>();
        mockHttpHandler
            .Protected()
            .Setup<Task<HttpResponseMessage>>(
                "SendAsync",
                ItExpr.IsAny<HttpRequestMessage>(),
                ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync((HttpRequestMessage request, CancellationToken _) =>
            {
                var isSearch = request.RequestUri!.AbsolutePath.Contains("search3");
                var isXml = navidromeXml && !isSearch && !request.RequestUri.Query.Contains("f=json");
                var body = isSearch
                    ? navidromeSearchJson ?? EmptyNavidromeSearchJson
                    : isXml ? NavidromeArtistXml : NavidromeArtistJson;
                if (request.RequestUri.AbsolutePath.Contains("getArtistInfo"))
                {
                    var element = request.RequestUri.AbsolutePath.EndsWith("2") ? "artistInfo2" : "artistInfo";
                    body = isXml
                        ? $"<subsonic-response xmlns=\"http://subsonic.org/restapi\" status=\"ok\"><{element}><biography>Unrelated band</biography><largeImageUrl>https://wrong.example/photo.jpg</largeImageUrl></{element}></subsonic-response>"
                        : JsonSerializer.Serialize(new Dictionary<string, object> { ["subsonic-response"] = new Dictionary<string, object> { ["status"] = "ok", [element] = new { biography = "Unrelated band", largeImageUrl = "https://wrong.example/photo.jpg" } } });
                }
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(body, System.Text.Encoding.UTF8, isXml ? "application/xml" : "application/json")
                };
            });

        var httpClient = new HttpClient(mockHttpHandler.Object);
        var mockHttpClientFactory = new Mock<IHttpClientFactory>();
        mockHttpClientFactory.Setup(x => x.CreateClient(It.IsAny<string>())).Returns(httpClient);

        var proxyService = new SubsonicProxyService(
            mockHttpClientFactory.Object,
            settings,
            new HttpContextAccessor { HttpContext = new DefaultHttpContext() });

        var localLibraryServiceMock = new Mock<ILocalLibraryService>();
        localLibraryServiceMock
            .Setup(x => x.ParseSongId(It.IsAny<string>()))
            .Returns(parsedId);

        var controller = new SubsonicController(
            settings,
            metadataServiceMock.Object,
            localLibraryServiceMock.Object,
            new Mock<IDownloadService>().Object,
            requestParser,
            responseBuilder,
            modelMapper,
            proxyService,
            new Mock<IHostApplicationLifetime>().Object,
            new Mock<ILogger<SubsonicController>>().Object);

        var httpContext = new DefaultHttpContext();
        httpContext.Request.QueryString = navidromeXml
            ? new QueryString($"?id={requestedId}")
            : new QueryString($"?id={requestedId}&f=json");
        controller.ControllerContext = new ControllerContext { HttpContext = httpContext };

        return controller;
    }

    private static List<string> GetMergedAlbumNames(IActionResult result)
        => GetMergedAlbums(result).Select(a => a.Name).ToList();

    private static List<(string Id, string Name)> GetMergedAlbums(IActionResult result)
    {
        var jsonResult = Assert.IsType<JsonResult>(result);
        var json = JsonSerializer.Serialize(jsonResult.Value);
        using var doc = JsonDocument.Parse(json);
        var albums = doc.RootElement
            .GetProperty("subsonic-response")
            .GetProperty("artist")
            .GetProperty("album");
        return albums.EnumerateArray()
            .Select(a => (
                a.GetProperty("id").GetString() ?? "",
                a.GetProperty("name").GetString() ?? ""))
            .ToList();
    }

    [Fact]
    public async Task GetArtist_WhenTopResultIsHomonym_PicksCandidateMatchingLocalAlbums()
    {
        var metadataServiceMock = new Mock<IMusicMetadataService>();
        metadataServiceMock
            .Setup(x => x.SearchArtistsAsync("Genesis", It.IsAny<int>()))
            .ReturnsAsync(new List<Artist>
            {
                new Artist { Id = "ext-deezer-artist-1", Name = "Genesis", ExternalProvider = "deezer", ExternalId = "1" },
                new Artist { Id = "ext-deezer-artist-2", Name = "Genesis", ExternalProvider = "deezer", ExternalId = "2" }
            });
        metadataServiceMock
            .Setup(x => x.GetArtistAlbumsAsync("deezer", "1"))
            .ReturnsAsync(new List<Album> { new Album { Id = "ext-deezer-album-11", Title = "Diamante" } });
        metadataServiceMock
            .Setup(x => x.GetArtistAlbumsAsync("deezer", "2"))
            .ReturnsAsync(new List<Album>
            {
                new Album { Id = "ext-deezer-album-21", Title = "We Can't Dance" },
                new Album { Id = "ext-deezer-album-22", Title = "Invisible Touch" }
            });

        var controller = CreateController(metadataServiceMock);

        var result = await controller.GetArtist();

        var albumNames = GetMergedAlbumNames(result);
        Assert.Contains("We Can't Dance", albumNames);
        Assert.Contains("Invisible Touch", albumNames);
        Assert.DoesNotContain("Diamante", albumNames);
    }

    [Fact]
    public async Task GetArtist_WhenExternalArtistExistsLocally_MergesOwnedAlbumsFirst()
    {
        var metadataServiceMock = new Mock<IMusicMetadataService>();
        metadataServiceMock
            .Setup(x => x.GetArtistAsync("deezer", "42"))
            .ReturnsAsync(new Artist { Id = "ext-deezer-artist-42", Name = "Genesis" });
        metadataServiceMock
            .Setup(x => x.GetArtistAlbumsAsync("deezer", "42"))
            .ReturnsAsync(new List<Album>
            {
                new Album { Id = "ext-deezer-album-21", Title = "We Can't Dance" },
                new Album { Id = "ext-deezer-album-22", Title = "Invisible Touch" }
            });

        var controller = CreateController(
            metadataServiceMock,
            "ext-deezer-artist-42",
            (true, "deezer", "42"),
            NavidromeSearchArtistJson);

        var result = await controller.GetArtist();

        var albums = GetMergedAlbums(result);
        Assert.Equal(new[] { "We Can't Dance", "Invisible Touch" }, albums.Select(a => a.Name));

        // The owned copy must win, otherwise playing it would download the album again
        Assert.Equal("local-album-1", albums[0].Id);
        Assert.Equal("ext-deezer-album-22", albums[1].Id);
    }

    [Fact]
    public async Task GetArtist_WhenExternalArtistIsUnknownLocally_KeepsProviderAlbumsOnly()
    {
        var metadataServiceMock = new Mock<IMusicMetadataService>();
        metadataServiceMock
            .Setup(x => x.GetArtistAsync("deezer", "42"))
            .ReturnsAsync(new Artist { Id = "ext-deezer-artist-42", Name = "Genesis" });
        metadataServiceMock
            .Setup(x => x.GetArtistAlbumsAsync("deezer", "42"))
            .ReturnsAsync(new List<Album> { new Album { Id = "ext-deezer-album-21", Title = "Invisible Touch" } });

        var controller = CreateController(
            metadataServiceMock,
            "ext-deezer-artist-42",
            (true, "deezer", "42"));

        var result = await controller.GetArtist();

        var albums = GetMergedAlbums(result);
        Assert.Equal("ext-deezer-album-21", Assert.Single(albums).Id);
    }

    [Fact]
    public async Task GetArtist_WhenClientAsksXml_AppendsExternalAlbumsToNavidromeArtist()
    {
        var metadataServiceMock = new Mock<IMusicMetadataService>();
        metadataServiceMock
            .Setup(x => x.SearchArtistsAsync("Genesis", It.IsAny<int>()))
            .ReturnsAsync(new List<Artist>
            {
                new Artist { Id = "ext-deezer-artist-1", Name = "Genesis", ExternalProvider = "deezer", ExternalId = "1" }
            });
        metadataServiceMock
            .Setup(x => x.GetArtistAlbumsAsync("deezer", "1"))
            .ReturnsAsync(new List<Album>
            {
                new Album { Id = "ext-deezer-album-11", Title = "We Can't Dance" },
                new Album { Id = "ext-deezer-album-12", Title = "Invisible Touch" }
            });

        var controller = CreateController(metadataServiceMock, navidromeXml: true);

        var result = await controller.GetArtist();

        var content = Assert.IsType<ContentResult>(result);
        var artist = XDocument.Parse(content.Content!).Root!.Elements()
            .Single(e => e.Name.LocalName == "artist");
        var albums = artist.Elements().Where(e => e.Name.LocalName == "album").ToList();

        Assert.Equal("2", artist.Attribute("albumCount")?.Value);
        Assert.Equal(new[] { "We Can't Dance", "Invisible Touch" }, albums.Select(a => a.Attribute("name")?.Value));
        Assert.Equal(new[] { "local-album-1", "ext-deezer-album-12" }, albums.Select(a => a.Attribute("id")?.Value));

        // Navidrome attributes of the owned album must survive the merge
        Assert.Equal("3", albums[0].Attribute("playCount")?.Value);
        Assert.Equal("12", albums[0].Attribute("songCount")?.Value);
    }

    private static Mock<IMusicMetadataService> AppleArtists(bool albumMatch = true, bool ambiguous = false)
    {
        var metadata = new Mock<IMusicMetadataService>();
        metadata.Setup(x => x.SearchArtistsAsync("Genesis", It.IsAny<int>())).ReturnsAsync(new List<Artist>
        {
            new() { Id = "ext-apple-artist-1", ExternalProvider = "apple", ExternalId = "1", Name = "Genesis" },
            new() { Id = "ext-apple-artist-2", ExternalProvider = "apple", ExternalId = "2", Name = "Genesis" }
        });
        metadata.Setup(x => x.GetArtistAlbumsAsync("apple", "1")).ReturnsAsync(new List<Album>
        { new() { Title = ambiguous ? "We Can't Dance" : "Other band's album", Id = "ext-apple-album-11" } });
        metadata.Setup(x => x.GetArtistAlbumsAsync("apple", "2")).ReturnsAsync(new List<Album>
        {
            new() { Title = albumMatch ? "We Can't Dance" : "Different album", Id = "ext-apple-album-21" },
            new() { Title = "Invisible Touch", Id = "ext-apple-album-22" }
        });
        metadata.Setup(x => x.GetArtistAsync("apple", "2")).ReturnsAsync(new Artist
        { Id = "ext-apple-artist-2", Name = "Genesis", ImageUrl = "https://apple.example/correct.jpg" });
        return metadata;
    }

    private static XElement ArtistResult(IActionResult result, bool xml, string element)
    {
        if (xml)
        {
            var body = result is ContentResult content ? content.Content! : System.Text.Encoding.UTF8.GetString(((FileContentResult)result).FileContents);
            return XDocument.Parse(body).Root!.Elements().Single(e => e.Name.LocalName == element);
        }
        var json = result is JsonResult data ? JsonSerializer.Serialize(data.Value) : System.Text.Encoding.UTF8.GetString(((FileContentResult)result).FileContents);
        using var doc = JsonDocument.Parse(json);
        var value = doc.RootElement.GetProperty("subsonic-response").GetProperty(element);
        return new XElement(element, value.EnumerateObject().Where(p => p.Value.ValueKind == JsonValueKind.String).Select(p => new XAttribute(p.Name, p.Value.GetString()!)));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task LocalAppleArtist_UsesMatchedPhotoAndRetainsLocalIdentity(bool xml)
    {
        var controller = CreateController(AppleArtists(), navidromeXml: xml, alacarte: true);
        for (var attempt = 0; attempt < 2; attempt++)
        {
            var result = await controller.GetArtist();
            var artist = ArtistResult(result, xml, "artist");
            Assert.Equal("local-artist-id", artist.Attribute("id")?.Value);
            Assert.Equal("ext-apple-artist-2", artist.Attribute("coverArt")?.Value);
            Assert.Equal("https://apple.example/correct.jpg", artist.Attribute("artistImageUrl")?.Value);
            if (!xml) Assert.Equal("local-album-1", GetMergedAlbums(result)[0].Id);
        }
    }

    [Theory]
    [InlineData(false, "getArtistInfo")]
    [InlineData(false, "getArtistInfo2")]
    [InlineData(true, "getArtistInfo")]
    [InlineData(true, "getArtistInfo2")]
    public async Task LocalAppleArtistInfo_MatchesPhotoAndDoesNotInheritHomonymBiography(bool xml, string endpoint)
    {
        var controller = CreateController(AppleArtists(), navidromeXml: xml, alacarte: true);
        controller.Request.Path = "/rest/" + endpoint;
        var info = ArtistResult(await controller.GetArtistInfo(), xml, endpoint[3..4].ToLowerInvariant() + endpoint[4..]);
        string? Field(string name) => xml ? info.Elements().SingleOrDefault(e => e.Name.LocalName == name)?.Value : info.Attribute(name)?.Value;
        Assert.Equal("https://apple.example/correct.jpg", Field("largeImageUrl"));
        Assert.Equal("https://apple.example/correct.jpg", Field("smallImageUrl"));
        Assert.Null(Field("biography"));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task LocalAppleArtist_WithoutUniqueAlbumEvidence_PreservesNavidrome(bool ambiguous)
    {
        var controller = CreateController(AppleArtists(albumMatch: ambiguous, ambiguous: ambiguous), alacarte: true);
        var result = await controller.GetArtist();
        var artist = ArtistResult(result, false, "artist");
        Assert.Equal("local-album-1", Assert.Single(GetMergedAlbums(result)).Id);
        Assert.Null(artist.Attribute("artistImageUrl"));
        controller.Request.Path = "/rest/getArtistInfo2";
        var info = ArtistResult(await controller.GetArtistInfo(), false, "artistInfo2");
        Assert.Equal("Unrelated band", info.Attribute("biography")?.Value);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task LocalAppleArtist_WhenCatalogUnavailable_RetainsLocalResponse(bool infoRequest)
    {
        var metadata = AppleArtists();
        metadata.Setup(x => x.GetArtistAlbumsAsync("apple", "1")).ThrowsAsync(new HttpRequestException("unavailable"));
        var controller = CreateController(metadata, alacarte: true);
        controller.Request.Path = "/rest/getArtistInfo2";
        var result = infoRequest ? await controller.GetArtistInfo() : await controller.GetArtist();
        var element = ArtistResult(result, false, infoRequest ? "artistInfo2" : "artist");
        Assert.Equal(infoRequest ? "Unrelated band" : "local-artist-id", element.Attribute(infoRequest ? "biography" : "id")?.Value);
    }
}

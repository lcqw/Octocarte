using System.Security.Cryptography;
using Microsoft.Extensions.Configuration;
using octo_fiesta.Services.Alacarte;

namespace octo_fiesta.Tests;

public class AlacarteAuthenticationTests
{
    private static string Token() => Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)).TrimEnd('=').Replace('+', '-').Replace('/', '_');
    private static IConfiguration Config(string? token, string? cookie = null) => new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?> {
        ["Alacarte:ServiceTokenFile"] = token, ["Alacarte:SessionCookieFile"] = cookie }).Build();

    [Fact]
    public void ServiceTokenHasPriorityAndRotationIsReadByNewClients()
    {
        var file = Path.GetTempFileName();
        try {
            var first = Token(); File.WriteAllText(file, first);
            using var client = new HttpClient();
            AlacarteAuthentication.Configure(client, Config(file, "cookie-must-not-be-read"));
            Assert.Equal("Bearer", client.DefaultRequestHeaders.Authorization!.Scheme);
            Assert.Equal(first, client.DefaultRequestHeaders.Authorization.Parameter);
            Assert.False(client.DefaultRequestHeaders.Contains("Cookie"));
            var second = Token(); File.WriteAllText(file, second);
            using var rotated = new HttpClient();
            AlacarteAuthentication.Configure(rotated, Config(file));
            Assert.Equal(second, rotated.DefaultRequestHeaders.Authorization!.Parameter);
        } finally { File.Delete(file); }
    }

    [Theory]
    [InlineData("")]
    [InlineData("invalid-secret-must-not-appear-in-errors")]
    [InlineData("header\r\ninjection")]
    public void InvalidTokenFailsWithoutLeakingOrFallingBack(string value)
    {
        var file = Path.GetTempFileName();
        try {
            File.WriteAllText(file, value);
            using var client = new HttpClient();
            var error = Assert.Throws<HttpRequestException>(() => AlacarteAuthentication.Configure(client, Config(file, "cookie-must-not-be-read")));
            Assert.Equal("ALACarte service token file is unavailable or invalid.", error.Message);
            Assert.Null(error.InnerException);
            Assert.False(client.DefaultRequestHeaders.Contains("Cookie"));
        } finally { File.Delete(file); }
    }

    [Fact]
    public void ExistingCookieDeploymentsStillWork()
    {
        var file = Path.GetTempFileName();
        try {
            File.WriteAllText(file, "fixture-session-cookie");
            using var client = new HttpClient();
            AlacarteAuthentication.Configure(client, Config(null, file));
            Assert.Equal("alacarte_session=fixture-session-cookie", Assert.Single(client.DefaultRequestHeaders.GetValues("Cookie")));
            Assert.Null(client.DefaultRequestHeaders.Authorization);
        } finally { File.Delete(file); }
    }
}

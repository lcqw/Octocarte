using System.Net.Http.Headers;
using System.Text.RegularExpressions;

namespace octo_fiesta.Services.Alacarte;

public static partial class AlacarteAuthentication
{
    [GeneratedRegex("^[A-Za-z0-9_-]{43}$", RegexOptions.CultureInvariant)]
    private static partial Regex TokenPattern();

    public static void Configure(HttpClient client, IConfiguration configuration)
    {
        var tokenFile = configuration["Alacarte:ServiceTokenFile"];
        if (!string.IsNullOrWhiteSpace(tokenFile))
        {
            string token;
            try
            {
                using var stream = File.OpenRead(tokenFile);
                if (stream.Length > 128) throw new InvalidOperationException();
                using var reader = new StreamReader(stream);
                token = reader.ReadToEnd().Trim();
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or InvalidOperationException)
            { throw new HttpRequestException("ALACarte service token file is unavailable or invalid."); }
            if (!TokenPattern().IsMatch(token))
                throw new HttpRequestException("ALACarte service token file is unavailable or invalid.");
            client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
            return; // A configured service token never falls back to a broad browser cookie.
        }

        var cookieFile = configuration["Alacarte:SessionCookieFile"];
        if (!string.IsNullOrWhiteSpace(cookieFile))
        {
            var cookie = File.ReadAllText(cookieFile).Trim();
            if (cookie.Length > 0) client.DefaultRequestHeaders.Add("Cookie", "alacarte_session=" + cookie);
        }
    }
}

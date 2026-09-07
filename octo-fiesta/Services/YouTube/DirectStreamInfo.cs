// Adapted from winters27/octo IDownloadService.cs and SubSonicController.cs.
// See NOTICE.OCTOCARTE.md. Keep response ownership until copying completes.
using Microsoft.AspNetCore.Mvc;

namespace octo_fiesta.Services.YouTube;

public sealed class DirectStreamInfo : IActionResult
{
    public required Stream AudioStream { get; init; }
    public required HttpResponseMessage Owner { get; init; }
    public required string ContentType { get; init; }
    public long? ContentLength { get; init; }
    public int StatusCode { get; init; } = 200;
    public string? ContentRange { get; init; }
    public async Task ExecuteResultAsync(ActionContext context)
    {
        using (Owner)
        await using (AudioStream)
        {
            var response = context.HttpContext.Response;
            response.StatusCode = StatusCode;
            response.ContentType = ContentType;
            response.Headers.AcceptRanges = "bytes";
            response.ContentLength = ContentLength;
            if (ContentRange is not null) response.Headers.ContentRange = ContentRange;
            try { await AudioStream.CopyToAsync(response.Body, context.HttpContext.RequestAborted); }
            catch (OperationCanceledException) when (context.HttpContext.RequestAborted.IsCancellationRequested) { }
        }
    }
}

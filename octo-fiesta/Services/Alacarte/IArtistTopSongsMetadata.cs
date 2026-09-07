using octo_fiesta.Models.Domain;

namespace octo_fiesta.Services.Alacarte;

public interface IArtistTopSongsMetadata
{
    // Null means the optional endpoint is unavailable; an empty list is a valid ranking.
    Task<List<Song>?> GetArtistTopSongsAsync(string artistId, int count);
}

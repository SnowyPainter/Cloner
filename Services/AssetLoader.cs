using System.IO;
using System.Text.Json;
using Cloner.Models;

namespace Cloner.Services
{
    public static class AssetLoader
    {
        public static AssetMetadata? Load(string assetFolder)
        {
            var path = Path.Combine(assetFolder, "asset.json");
            if (!File.Exists(path))
                return null;

            var json = File.ReadAllText(path);

            return JsonSerializer.Deserialize<AssetMetadata>(
                json,
                new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });
        }
    }
}

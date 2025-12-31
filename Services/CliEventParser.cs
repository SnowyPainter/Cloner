using Cloner.Models;
using System;
using System.Text.Json;

namespace Cloner.Services
{
    public static class CliEventParser
    {
        private static readonly JsonSerializerOptions Options = new()
        {
            PropertyNameCaseInsensitive = true
        };

        /// <summary>
        /// CLI JSON 이벤트 파싱.
        /// 파싱 불가 / 스키마 없음 / 알 수 없는 스키마 → null 반환 (조용히 무시)
        /// </summary>
        public static CliEvent? Parse(string json)
        {
            try
            {
                using var doc = JsonDocument.Parse(json);

                if (!doc.RootElement.TryGetProperty("schema", out var schemaProp))
                    return null;

                var schema = schemaProp.GetString();
                if (string.IsNullOrWhiteSpace(schema))
                    return null;

                return schema switch
                {
                    "reels.cli.ingest.v1"
                        => JsonSerializer.Deserialize<IngestOutput>(json, Options),

                    "reels.cli.build.v1"
                        => JsonSerializer.Deserialize<BuildOutput>(json, Options),

                    "reels.cli.log.v1"
                        => JsonSerializer.Deserialize<LogEvent>(json, Options),

                    _ => null // 알 수 없는 schema → 무시
                };
            }
            catch
            {
                // JSON 깨짐, 텍스트 로그, tqdm, ffmpeg 출력 등
                // 전부 무시
                return null;
            }
        }
    }
}

using System;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Cloner.Models
{
    // ---------- base ----------

    public abstract record CliEvent
    {
        [JsonPropertyName("schema")]
        public string Schema { get; init; } = default!;
    }

    // ---------- ingest ----------

    public sealed record IngestOutput : CliEvent
    {
        [JsonPropertyName("asset_id")]
        public string AssetId { get; init; } = default!;
    }

    // ---------- build ----------

    public sealed record BuildOutput : CliEvent
    {
        [JsonPropertyName("asset_id")]
        public string AssetId { get; init; } = default!;

        [JsonPropertyName("output_path")]
        public string OutputPath { get; init; } = default!;
    }

    // ---------- log ----------

    public sealed record LogEvent : CliEvent
    {
        [JsonPropertyName("ts")]
        public DateTime Timestamp { get; init; }

        [JsonPropertyName("level")]
        public string Level { get; init; } = default!;

        [JsonPropertyName("logger")]
        public string Logger { get; init; } = default!;

        [JsonPropertyName("message")]
        public string Message { get; init; } = default!;

        [JsonPropertyName("error")]
        public LogError? Error { get; init; }

        [JsonPropertyName("extra")]
        public JsonElement? Extra { get; init; }
    }

    public sealed record LogError
    {
        [JsonPropertyName("type")]
        public string Type { get; init; } = default!;

        [JsonPropertyName("message")]
        public string Message { get; init; } = default!;
    }
}

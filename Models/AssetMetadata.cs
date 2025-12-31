using System;
using System.Collections.Generic;
using System.Text;

namespace Cloner.Models
{
    public class AssetMetadata
    {
        public string AssetId { get; set; } = "";
        public string Source { get; set; } = "";
        public string YoutubeId { get; set; } = "";
        public string Title { get; set; } = "";
        public double Duration { get; set; }
        public DateTime CreatedAt { get; set; }
    }
}
